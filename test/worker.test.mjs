import test from 'node:test';
import assert from 'node:assert/strict';

import {
  sha256Hex,
  hashNormalized,
  normEmail,
  normPhoneMeta,
  normPhoneTikTok,
  normText,
  verifyShopifyHmac
} from '../worker/src/crypto.js';

import worker from '../worker/src/index.js';

/* ── Hachage ──────────────────────────────────────────────────────────────── */

test('sha256Hex produit le condensé de référence', async () => {
  // Vecteur de test standard : SHA-256 de la chaîne vide.
  assert.equal(
    await sha256Hex(''),
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
  );
});

test('Meta et TikTok reçoivent des hachages de téléphone différents', async () => {
  // Divergence assumée entre les deux specs : Meta veut les chiffres seuls,
  // TikTok l'E.164 avec le "+". Mutualiser casserait le matching de l'une des deux.
  assert.equal(normPhoneMeta('+212612345678'), '212612345678');
  assert.equal(normPhoneTikTok('+212612345678'), '+212612345678');

  const meta = await hashNormalized('+212612345678', normPhoneMeta);
  const tiktok = await hashNormalized('+212612345678', normPhoneTikTok);
  assert.notEqual(meta, tiktok, 'les deux hachages doivent différer');
});

test('une valeur vide ne produit jamais de hachage', async () => {
  // Hacher "" donnerait une constante partagée par tous les visiteurs sans
  // téléphone, ce que les plateformes interpréteraient comme un même individu.
  for (const vide of ['', '   ', null, undefined]) {
    assert.equal(await hashNormalized(vide, normPhoneMeta), null, `pour ${JSON.stringify(vide)}`);
  }
});

test('normalisation du texte : accents, casse et ponctuation', async () => {
  assert.equal(normText('  Casablanca '), 'casablanca');
  assert.equal(normText('Kénitra'), 'kenitra');
  assert.equal(normText('Sidi-Bennour'), 'sidibennour');
  assert.equal(normText('SALÉ'), 'sale');
  assert.equal(normEmail('  Client@KLAXO.MA '), 'client@klaxo.ma');
});

/* ── HMAC Shopify ─────────────────────────────────────────────────────────── */

async function signShopify(body, secret) {
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(body));
  return Buffer.from(new Uint8Array(sig)).toString('base64');
}

test('une signature valide est acceptée, une signature altérée est refusée', async () => {
  const secret = 'secret-de-test';
  const body = JSON.stringify({ id: 1234, total_price: '349.00' });
  const signature = await signShopify(body, secret);

  assert.equal(await verifyShopifyHmac(body, signature, secret), true);

  // Corps modifié après signature : c'est exactement l'attaque que le HMAC bloque.
  const falsifie = JSON.stringify({ id: 1234, total_price: '1.00' });
  assert.equal(await verifyShopifyHmac(falsifie, signature, secret), false);

  // Mauvaise clé.
  assert.equal(await verifyShopifyHmac(body, signature, 'autre-secret'), false);
});

test('signature absente ou illisible : refus sans exception', async () => {
  const body = '{}';
  for (const mauvaise of [null, '', 'pas-du-base64!!', '###']) {
    assert.equal(await verifyShopifyHmac(body, mauvaise, 'secret'), false, `pour ${mauvaise}`);
  }
  // Secret non configuré : refuser plutôt que laisser passer.
  assert.equal(await verifyShopifyHmac(body, 'abcd', ''), false);
});

/* ── Routes ───────────────────────────────────────────────────────────────── */

const ENV = {
  ALLOWED_ORIGINS: 'https://klaxo.ma',
  STORE_URL: 'https://klaxo.ma',
  META_PIXEL_ID: 'pixel',
  META_CAPI_TOKEN: 'token',
  TIKTOK_PIXEL_CODE: 'code',
  TIKTOK_ACCESS_TOKEN: 'token',
  SHOPIFY_WEBHOOK_SECRET: 'secret-de-test',
  LIFECYCLE_TOKEN: 'token-interne'
};

const post = (path, body, headers = {}) =>
  new Request(`https://w.klaxo.ma${path}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', ...headers },
    body: typeof body === 'string' ? body : JSON.stringify(body)
  });

test('/collect refuse Purchase depuis le navigateur', async () => {
  // Le cœur de la décision de sécurité : une route publique ne doit pas pouvoir
  // injecter de conversions, sinon l'optimisation et le CPA sont empoisonnés.
  const res = await worker.fetch(
    post('/collect', { event_name: 'Purchase', event_id: 'x' }, { Origin: 'https://klaxo.ma' }),
    ENV
  );
  assert.equal(res.status, 400);
  const body = await res.json();
  assert.equal(body.error, 'event_not_allowed_from_browser');
});

test('/collect refuse une origine non déclarée', async () => {
  const res = await worker.fetch(
    post('/collect', { event_name: 'ViewContent', event_id: 'x' }, { Origin: 'https://pirate.example' }),
    ENV
  );
  assert.equal(res.status, 403);
});

test('/collect exige un event_id pour permettre la déduplication', async () => {
  const res = await worker.fetch(
    post('/collect', { event_name: 'ViewContent' }, { Origin: 'https://klaxo.ma' }),
    ENV
  );
  assert.equal(res.status, 400);
  assert.equal((await res.json()).error, 'missing_event_id');
});

test('le webhook refuse une commande non signée', async () => {
  const res = await worker.fetch(post('/webhooks/shopify/orders-create', { id: 1 }), ENV);
  assert.equal(res.status, 401);
  assert.equal((await res.json()).error, 'invalid_signature');
});

test('webhook signé : un Purchase par commande, attribution relue du panier', async () => {
  const envoyes = [];
  const fetchOriginal = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    envoyes.push({ url: String(url), body: JSON.parse(init.body) });
    return new Response('{}', { status: 200 });
  };

  try {
    // Deux commandes du même navigateur : mêmes attributs de panier.
    const attributs = [
      { name: 'klaxo_fbc', value: 'fb.1.1700000000000.ABC' },
      { name: 'klaxo_utm_source', value: 'facebook' }
    ];
    for (const id of [101, 102]) {
      const body = JSON.stringify({ id, total_price: '349.00', currency: 'MAD', note_attributes: attributs });
      const res = await worker.fetch(
        post('/webhooks/shopify/orders-create', body, {
          'X-Shopify-Hmac-Sha256': await signShopify(body, ENV.SHOPIFY_WEBHOOK_SECRET)
        }),
        ENV
      );
      assert.equal(res.status, 200);
    }

    const meta = envoyes.filter((e) => e.url.includes('facebook.com')).map((e) => e.body.data[0]);
    assert.equal(meta.length, 2);
    // Un identifiant commun ferait fusionner par Meta la 2e commande avec la 1re.
    assert.deepEqual(meta.map((e) => e.event_id), ['order_101', 'order_102']);
    assert.equal(meta[0].user_data.fbc, 'fb.1.1700000000000.ABC');
  } finally {
    globalThis.fetch = fetchOriginal;
  }
});

test('/lifecycle exige le jeton interne et un événement connu', async () => {
  const sansJeton = await worker.fetch(
    post('/lifecycle', { event_name: 'order_confirmed', order_id: 1 }),
    ENV
  );
  assert.equal(sansJeton.status, 401);

  const inconnu = await worker.fetch(
    post('/lifecycle', { event_name: 'order_teleporte', order_id: 1 }, { 'X-Klaxo-Token': 'token-interne' }),
    ENV
  );
  assert.equal(inconnu.status, 400);
  assert.equal((await inconnu.json()).error, 'unknown_lifecycle_event');
});

test('/health signale la configuration sans divulguer de secret', async () => {
  const res = await worker.fetch(new Request('https://w.klaxo.ma/health'), ENV);
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.deepEqual(body.configured, { meta: true, tiktok: true, webhook: true, lifecycle: true });

  // Aucune valeur de secret ne doit apparaître dans la réponse.
  const brut = JSON.stringify(body);
  for (const secret of ['token', 'secret-de-test', 'token-interne', 'pixel', 'code']) {
    assert.equal(brut.includes(secret), false, `le secret "${secret}" fuite dans /health`);
  }
});

test('une route inconnue renvoie 404', async () => {
  const res = await worker.fetch(new Request('https://w.klaxo.ma/nimporte'), ENV);
  assert.equal(res.status, 404);
});
