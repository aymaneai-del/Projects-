/*
 * KLAXO — Meta Conversions API.
 *
 * Déduplication : chaque événement porte un event_id généré côté navigateur et
 * réutilisé tel quel côté serveur. Meta rapproche les deux envois et n'en compte
 * qu'un. Sans event_id partagé, chaque conversion serait comptée deux fois et le
 * CPA affiché serait divisé par deux — une erreur qui pousse à surinvestir.
 */

import { hashNormalized, normEmail, normPhoneMeta, normText } from './crypto.js';

const GRAPH_VERSION = 'v21.0';

/**
 * Construit le bloc user_data attendu par Meta.
 * Toutes les données personnelles sont hachées en SHA-256 ; seules les valeurs
 * techniques (IP, user-agent, cookies fbp/fbc) partent en clair, comme l'exige
 * la spécification.
 */
async function buildUserData(user, context) {
  const [ph, em, ct] = await Promise.all([
    hashNormalized(user.phone, normPhoneMeta),
    hashNormalized(user.email, normEmail),
    hashNormalized(user.city, normText)
  ]);

  const data = {};
  // Meta attend des tableaux pour les champs hachés.
  if (ph) data.ph = [ph];
  if (em) data.em = [em];
  if (ct) data.ct = [ct];
  // Le pays est constant sur ce store : toutes les livraisons sont marocaines.
  data.country = [await hashNormalized('ma', normText)];

  if (context.ip) data.client_ip_address = context.ip;
  if (context.userAgent) data.client_user_agent = context.userAgent;
  if (user.fbp) data.fbp = user.fbp;
  if (user.fbc) data.fbc = user.fbc;

  return data;
}

/**
 * Envoie un événement à Meta.
 * @returns {Promise<{ok: boolean, status: number, body: string}>}
 */
export async function sendMetaEvent(event, context, env) {
  const userData = await buildUserData(event.user || {}, context);

  const payload = {
    data: [
      {
        event_name: event.name,
        event_id: event.id,
        event_time: event.time,
        action_source: 'website',
        event_source_url: event.sourceUrl,
        user_data: userData,
        custom_data: event.custom || {}
      }
    ]
  };

  // Code de test : présent uniquement en recette, jamais en production.
  // Un événement portant ce code n'alimente PAS l'optimisation des campagnes.
  if (env.META_TEST_EVENT_CODE) {
    payload.test_event_code = env.META_TEST_EVENT_CODE;
  }

  const url = `https://graph.facebook.com/${GRAPH_VERSION}/${env.META_PIXEL_ID}/events` +
    `?access_token=${encodeURIComponent(env.META_CAPI_TOKEN)}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload)
  });

  const body = await response.text();
  return { ok: response.ok, status: response.status, body };
}
