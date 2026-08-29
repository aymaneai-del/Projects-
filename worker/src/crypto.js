/*
 * KLAXO — primitives cryptographiques du Worker.
 *
 * Deux responsabilités, volontairement séparées du reste :
 *   1. Hacher les données personnelles avant de les envoyer à Meta / TikTok.
 *   2. Vérifier la signature HMAC des webhooks Shopify.
 *
 * Web Crypto API : disponible nativement dans Cloudflare Workers, aucune dépendance.
 */

const encoder = new TextEncoder();

/**
 * SHA-256 en hexadécimal minuscule.
 * Meta et TikTok exigent tous deux ce format pour les données utilisateur.
 */
export async function sha256Hex(value) {
  const buffer = await crypto.subtle.digest('SHA-256', encoder.encode(value));
  return Array.from(new Uint8Array(buffer))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * Hache une donnée personnelle après normalisation.
 * Renvoie null si la valeur est vide — il ne faut JAMAIS envoyer le hash d'une
 * chaîne vide : c'est une valeur constante qui ferait correspondre entre eux
 * tous les visiteurs sans téléphone.
 */
export async function hashNormalized(value, normalizer) {
  if (value === null || value === undefined) return null;
  const normalized = normalizer(String(value));
  if (!normalized) return null;
  return sha256Hex(normalized);
}

/** Meta : e-mail en minuscules, sans espaces autour. */
export const normEmail = (v) => v.trim().toLowerCase();

/**
 * Meta : téléphone en chiffres uniquement, indicatif pays compris, sans "+".
 * TikTok : téléphone en E.164, "+" compris.
 * Les deux plateformes divergent ici — d'où deux normaliseurs distincts plutôt
 * qu'un seul "à peu près bon" qui casserait silencieusement le matching de l'une.
 */
export const normPhoneMeta = (v) => v.replace(/\D/g, '');
export const normPhoneTikTok = (v) => {
  const digits = v.replace(/\D/g, '');
  return digits ? `+${digits}` : '';
};

/** Ville / prénom / nom : minuscules, sans espaces ni accents ni ponctuation. */
export const normText = (v) =>
  v
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]/g, '');

/**
 * Vérifie la signature HMAC-SHA256 d'un webhook Shopify.
 *
 * IMPORTANT : doit recevoir le corps BRUT de la requête. Un JSON.parse puis
 * re-stringify change les octets et invalide la signature.
 *
 * crypto.subtle.verify effectue une comparaison à temps constant, ce qui évite
 * la fuite par timing d'une comparaison de chaînes naïve.
 */
export async function verifyShopifyHmac(rawBody, headerValue, secret) {
  if (!headerValue || !secret) return false;

  let signature;
  try {
    // Shopify transmet la signature en base64.
    signature = Uint8Array.from(atob(headerValue), (c) => c.charCodeAt(0));
  } catch {
    return false;
  }

  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['verify']
  );

  return crypto.subtle.verify('HMAC', key, signature, encoder.encode(rawBody));
}
