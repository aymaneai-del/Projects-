/*
 * KLAXO — Worker de tracking server-side (Phase 2).
 *
 * Quatre routes, une responsabilité chacune :
 *   GET  /health                          état du service
 *   POST /collect                         événements de navigation (navigateur)
 *   POST /webhooks/shopify/orders-create  commande passée → Purchase
 *   POST /lifecycle                       confirmation / livraison (mesure)
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * DÉCISION DE SÉCURITÉ — pourquoi /collect refuse Purchase
 *
 * /collect est une route publique : n'importe qui peut la découvrir dans le code
 * de la page et lui envoyer ce qu'il veut. Si elle acceptait Purchase, un tiers
 * pourrait injecter de fausses conversions dans le pixel — ce qui empoisonnerait
 * l'optimisation des campagnes et fausserait le CPA, donc les décisions de kill.
 *
 * Purchase provient donc EXCLUSIVEMENT du webhook Shopify, dont la signature HMAC
 * prouve l'origine. /collect ne porte que des événements de navigation, sans
 * valeur monétaire et sans conséquence s'ils sont bruités.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { verifyShopifyHmac } from './crypto.js';
import { sendMetaEvent } from './meta.js';
import { sendTikTokEvent } from './tiktok.js';

/** Événements que le navigateur a le droit de déclencher. */
const BROWSER_ALLOWED = new Set(['ViewContent', 'InitiateCheckout']);

/** Événements métier propres au COD — mesure uniquement, jamais l'optimisation. */
const LIFECYCLE_ALLOWED = new Set(['order_confirmed', 'order_delivered']);

const json = (data, status = 200, extraHeaders = {}) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'content-type': 'application/json', ...extraHeaders }
  });

function corsHeaders(request, env) {
  const origin = request.headers.get('Origin') || '';
  const allowed = (env.ALLOWED_ORIGINS || '')
    .split(',')
    .map((o) => o.trim())
    .filter(Boolean);

  // Pas de "*" : seules les origines déclarées du store peuvent appeler /collect.
  if (!allowed.includes(origin)) return null;

  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'content-type',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin'
  };
}

function requestContext(request) {
  return {
    ip: request.headers.get('CF-Connecting-IP') || null,
    userAgent: request.headers.get('User-Agent') || null
  };
}

/**
 * Diffuse un événement vers les deux plateformes.
 *
 * Les deux envois sont indépendants : un échec Meta ne doit pas empêcher TikTok.
 * Chaque échec est journalisé avec sa référence — un événement perdu en silence
 * produit un CPA faux, donc une décision de kill fausse.
 */
async function fanOut(event, context, env, reference) {
  const results = await Promise.allSettled([
    sendMetaEvent(event, context, env),
    sendTikTokEvent(event, context, env)
  ]);

  const summary = { meta: null, tiktok: null };
  const platforms = ['meta', 'tiktok'];

  results.forEach((result, i) => {
    const platform = platforms[i];
    if (result.status === 'rejected') {
      summary[platform] = { ok: false, error: String(result.reason) };
      console.error(
        `[klaxo] ENVOI ÉCHOUÉ platform=${platform} event=${event.name} ` +
        `ref=${reference} raison=réseau détail=${result.reason}`
      );
      return;
    }
    summary[platform] = { ok: result.value.ok, status: result.value.status };
    if (!result.value.ok) {
      console.error(
        `[klaxo] ENVOI REFUSÉ platform=${platform} event=${event.name} ` +
        `ref=${reference} status=${result.value.status} corps=${result.value.body}`
      );
    }
  });

  return summary;
}

/* ── POST /collect ───────────────────────────────────────────────────────── */

async function handleCollect(request, env) {
  const cors = corsHeaders(request, env);
  if (!cors) return json({ error: 'origin_not_allowed' }, 403);

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'invalid_json' }, 400, cors);
  }

  if (!BROWSER_ALLOWED.has(body.event_name)) {
    // Refus explicite et documenté : voir la note de sécurité en tête de fichier.
    return json(
      { error: 'event_not_allowed_from_browser', allowed: [...BROWSER_ALLOWED] },
      400,
      cors
    );
  }
  if (!body.event_id) {
    // Sans event_id, la déduplication est impossible et l'événement serait
    // compté deux fois. Mieux vaut le refuser que fausser la mesure.
    return json({ error: 'missing_event_id' }, 400, cors);
  }

  const event = {
    name: body.event_name,
    id: body.event_id,
    time: Math.floor(Date.now() / 1000),
    sourceUrl: body.url || null,
    user: body.user || {},
    custom: body.custom || {}
  };

  const summary = await fanOut(event, requestContext(request), env, `collect:${event.id}`);
  return json({ received: true, event_id: event.id, platforms: summary }, 200, cors);
}

/* ── POST /webhooks/shopify/orders-create ────────────────────────────────── */

/**
 * Récupère une note_attribute par son nom.
 * C'est par ce canal que l'event_id du navigateur et les UTM voyagent jusqu'ici :
 * le formulaire les dépose dans la commande, le webhook les relit.
 */
function noteAttribute(order, name) {
  const attributes = order.note_attributes || [];
  const found = attributes.find((a) => a && a.name === name);
  return found ? found.value : null;
}

async function handleShopifyWebhook(request, env) {
  // Le corps BRUT est indispensable : parser puis re-sérialiser changerait les
  // octets et invaliderait la signature.
  const rawBody = await request.text();
  const signature = request.headers.get('X-Shopify-Hmac-Sha256');

  const valid = await verifyShopifyHmac(rawBody, signature, env.SHOPIFY_WEBHOOK_SECRET);
  if (!valid) {
    console.error('[klaxo] WEBHOOK REJETÉ signature=invalide');
    return json({ error: 'invalid_signature' }, 401);
  }

  let order;
  try {
    order = JSON.parse(rawBody);
  } catch {
    return json({ error: 'invalid_json' }, 400);
  }

  const reference = `order:${order.id ?? 'inconnu'}`;

  // L'event_id vient du navigateur via le formulaire. S'il manque, on retombe
  // sur un identifiant dérivé de la commande : l'événement part quand même
  // (perdre un Purchase coûte plus cher qu'un doublon), mais on le signale.
  let eventId = noteAttribute(order, 'klaxo_event_id');
  if (!eventId) {
    eventId = `order_${order.id}`;
    console.warn(
      `[klaxo] event_id absent des note_attributes ${reference} — ` +
      `déduplication navigateur impossible pour cette commande`
    );
  }

  const shipping = order.shipping_address || {};
  const customer = order.customer || {};

  const event = {
    name: 'Purchase',
    id: eventId,
    time: Math.floor(Date.now() / 1000),
    sourceUrl: noteAttribute(order, 'klaxo_landing_url') || env.STORE_URL || null,
    user: {
      phone: order.phone || shipping.phone || customer.phone || null,
      email: order.email || customer.email || null,
      city: shipping.city || null,
      fbp: noteAttribute(order, 'klaxo_fbp'),
      fbc: noteAttribute(order, 'klaxo_fbc'),
      ttp: noteAttribute(order, 'klaxo_ttp'),
      ttclid: noteAttribute(order, 'klaxo_ttclid')
    },
    custom: {
      currency: order.currency || 'MAD',
      value: Number(order.total_price) || 0,
      content_type: 'product',
      contents: (order.line_items || []).map((item) => ({
        content_id: String(item.product_id ?? item.sku ?? ''),
        quantity: item.quantity,
        item_price: Number(item.price) || 0
      }))
    }
  };

  const summary = await fanOut(event, requestContext(request), env, reference);

  // Toujours 200 vers Shopify : un non-2xx déclenche des relances, donc des
  // Purchase en double. Les échecs de diffusion sont journalisés, pas rejoués ici.
  return json({ received: true, order_id: order.id, platforms: summary });
}

/* ── POST /lifecycle ─────────────────────────────────────────────────────── */

/**
 * Confirmation téléphonique et livraison payée.
 *
 * Ces deux événements servent à la MESURE, jamais à l'optimisation : au budget
 * du projet, le volume de confirmations n'atteindra pas les ~50/semaine/ad set
 * que Meta exige pour sortir de la phase d'apprentissage. Optimiser dessus
 * bloquerait l'algorithme en apprentissage et ferait exploser le coût par résultat.
 */
async function handleLifecycle(request, env) {
  // Route appelée par des outils internes, pas par le navigateur : un secret
  // partagé suffit et évite d'exposer une route d'écriture sans authentification.
  const token = request.headers.get('X-Klaxo-Token');
  if (!env.LIFECYCLE_TOKEN || token !== env.LIFECYCLE_TOKEN) {
    return json({ error: 'unauthorized' }, 401);
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'invalid_json' }, 400);
  }

  if (!LIFECYCLE_ALLOWED.has(body.event_name)) {
    return json(
      { error: 'unknown_lifecycle_event', allowed: [...LIFECYCLE_ALLOWED] },
      400
    );
  }
  if (!body.order_id) return json({ error: 'missing_order_id' }, 400);

  const event = {
    name: body.event_name,
    // Un identifiant par couple (commande, étape) : une commande confirmée puis
    // livrée produit deux événements distincts, chacun dédupliqué séparément.
    id: `${body.event_name}_${body.order_id}`,
    time: Math.floor(Date.now() / 1000),
    sourceUrl: env.STORE_URL || null,
    user: { phone: body.phone || null, email: body.email || null, city: body.city || null },
    custom: {
      currency: body.currency || 'MAD',
      value: Number(body.value) || 0,
      order_id: String(body.order_id)
    }
  };

  const summary = await fanOut(event, requestContext(request), env, `order:${body.order_id}`);
  return json({ received: true, event: event.name, order_id: body.order_id, platforms: summary });
}

/* ── Routeur ─────────────────────────────────────────────────────────────── */

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);

    if (request.method === 'OPTIONS' && pathname === '/collect') {
      const cors = corsHeaders(request, env);
      return cors
        ? new Response(null, { status: 204, headers: cors })
        : json({ error: 'origin_not_allowed' }, 403);
    }

    if (request.method === 'GET' && pathname === '/health') {
      // Aucune valeur de secret n'est renvoyée : uniquement leur présence,
      // pour diagnostiquer une configuration incomplète sans rien divulguer.
      return json({
        ok: true,
        configured: {
          meta: Boolean(env.META_PIXEL_ID && env.META_CAPI_TOKEN),
          tiktok: Boolean(env.TIKTOK_PIXEL_CODE && env.TIKTOK_ACCESS_TOKEN),
          webhook: Boolean(env.SHOPIFY_WEBHOOK_SECRET),
          lifecycle: Boolean(env.LIFECYCLE_TOKEN)
        }
      });
    }

    if (request.method === 'POST') {
      if (pathname === '/collect') return handleCollect(request, env);
      if (pathname === '/webhooks/shopify/orders-create') return handleShopifyWebhook(request, env);
      if (pathname === '/lifecycle') return handleLifecycle(request, env);
    }

    return json({ error: 'not_found' }, 404);
  }
};
