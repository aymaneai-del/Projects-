/*
 * KLAXO — TikTok Events API (v1.3).
 *
 * Même logique de déduplication que Meta : l'event_id du navigateur est réutilisé
 * côté serveur. TikTok l'attend dans data[].event_id.
 *
 * Divergence à connaître : TikTok veut le téléphone en E.164 AVEC le "+" avant
 * hachage, là où Meta le veut en chiffres seuls. D'où deux normaliseurs distincts
 * dans crypto.js — les mutualiser casserait silencieusement le matching de l'une
 * des deux plateformes, sans aucune erreur visible.
 */

import { hashNormalized, normEmail, normPhoneTikTok } from './crypto.js';

const ENDPOINT = 'https://business-api.tiktok.com/open_api/v1.3/event/track/';

/**
 * Correspondance entre nos noms d'événements internes et ceux de TikTok.
 * Les événements métier propres au COD (confirmation, livraison) n'ont pas
 * d'équivalent standard : ils partent sous leur nom, en événement personnalisé.
 */
const EVENT_MAP = {
  ViewContent: 'ViewContent',
  InitiateCheckout: 'InitiateCheckout',
  Purchase: 'CompletePayment'
};

export async function sendTikTokEvent(event, context, env) {
  const [phone, email] = await Promise.all([
    hashNormalized(event.user?.phone, normPhoneTikTok),
    hashNormalized(event.user?.email, normEmail)
  ]);

  const user = {};
  if (phone) user.phone = phone;
  if (email) user.email = email;
  if (context.ip) user.ip = context.ip;
  if (context.userAgent) user.user_agent = context.userAgent;
  if (event.user?.ttp) user.ttp = event.user.ttp;
  if (event.user?.ttclid) user.ttclid = event.user.ttclid;

  const payload = {
    event_source: 'web',
    event_source_id: env.TIKTOK_PIXEL_CODE,
    data: [
      {
        event: EVENT_MAP[event.name] || event.name,
        event_time: event.time,
        event_id: event.id,
        user,
        page: { url: event.sourceUrl },
        properties: event.custom || {}
      }
    ]
  };

  if (env.TIKTOK_TEST_EVENT_CODE) {
    payload.test_event_code = env.TIKTOK_TEST_EVENT_CODE;
  }

  const response = await fetch(ENDPOINT, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'Access-Token': env.TIKTOK_ACCESS_TOKEN
    },
    body: JSON.stringify(payload)
  });

  const body = await response.text();

  // Piège TikTok : l'API répond 200 même en cas d'erreur applicative.
  // Le seul indicateur fiable est le champ "code" du corps, où 0 signifie succès.
  let applicationOk = response.ok;
  try {
    const parsed = JSON.parse(body);
    if (typeof parsed.code === 'number') applicationOk = parsed.code === 0;
  } catch {
    // Réponse non-JSON : on s'en tient au statut HTTP.
  }

  return { ok: applicationOk, status: response.status, body };
}
