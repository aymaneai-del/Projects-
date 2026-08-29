/*
 * KLAXO — normalisation des numéros de téléphone marocains.
 *
 * Règle du projet : chaque rejet de formulaire est une commande perdue et un CPA
 * gaspillé. On accepte donc TOUTES les façons dont un Marocain écrit son numéro,
 * et on ne refuse que ce qui ne peut pas être un numéro marocain.
 *
 * Formats acceptés en entrée (avec espaces, tirets, points, parenthèses libres) :
 *   0612345678      06 12 34 56 78     06-12-34-56-78
 *   0712345678      0522334455         05.22.33.44.55
 *   +212612345678   +212 6 12 34 56 78
 *   212612345678    00212612345678
 *   612345678       (sans le zéro initial)
 *
 * Sortie canonique : E.164 → "+212XXXXXXXXX"
 *
 * Module sans dépendance, utilisable dans le thème (window.KlaxoPhone)
 * comme dans le Worker et les tests (export ESM).
 */

// Préfixes nationaux valides au Maroc, une fois le 0 initial retiré :
//   5 → fixe (05 22 Casablanca, 05 37 Rabat, …)
//   6 → mobile historique
//   7 → mobile (plages ouvertes plus récemment)
var KLAXO_NATIONAL_PREFIXES = ['5', '6', '7'];
var KLAXO_NATIONAL_LENGTH = 9;

/**
 * Normalise une saisie utilisateur en numéro marocain E.164.
 *
 * @param {string} input Saisie brute du formulaire.
 * @returns {{ok: boolean, e164: string|null, national: string|null, reason: string|null}}
 *   ok       — true si le numéro est exploitable
 *   e164     — "+212XXXXXXXXX" (à stocker et à afficher)
 *   national — "XXXXXXXXX" (9 chiffres, sans indicatif ni zéro)
 *   reason   — code d'erreur stable, jamais un message destiné à l'utilisateur
 */
function klaxoNormalizePhone(input) {
  var fail = function (reason) {
    return { ok: false, e164: null, national: null, reason: reason };
  };

  if (typeof input !== 'string') return fail('not_a_string');

  // 1. Ne garder que les chiffres, en mémorisant si l'utilisateur a écrit un "+".
  //    Tout le reste (espaces, tirets, points, parenthèses, lettres) est du bruit
  //    de saisie et ne doit jamais provoquer un rejet.
  var hadPlus = input.trim().charAt(0) === '+';
  var digits = input.replace(/\D/g, '');

  if (digits.length === 0) return fail('empty');

  // 2. Écarter les numéros étrangers AVANT de tenter une interprétation marocaine.
  //    Livrer hors Maroc n'est pas dans le périmètre, et tordre un numéro français
  //    en numéro marocain produirait un appel de confirmation dans le vide.
  //    Deux marqueurs d'international : le "+" et le préfixe de sortie "00".
  var isInternational = hadPlus || digits.indexOf('00') === 0;
  var isMoroccan = digits.indexOf('212') === 0 || digits.indexOf('00212') === 0;
  if (isInternational && !isMoroccan) {
    return fail('foreign_number');
  }

  // 3. Ramener toutes les écritures de l'indicatif à un seul cas.
  //    L'ordre compte : "00212…" avant "212…".
  //    Aucune ambiguïté possible ici : un numéro national commence par 5, 6 ou 7,
  //    donc une chaîne débutant par "212" est forcément un indicatif.
  var national;
  if (digits.indexOf('00212') === 0) {
    national = digits.slice(5);
  } else if (digits.indexOf('212') === 0) {
    national = digits.slice(3);
  } else if (digits.charAt(0) === '0') {
    national = digits.slice(1);
  } else {
    // Saisie sans zéro ni indicatif : "612345678".
    national = digits;
  }

  // 4. Absorber le zéro d'appel national écrit après l'indicatif, notation
  //    fréquente sur les cartes de visite : "+212 (0) 6 12 34 56 78".
  //    Sans danger : un numéro national valide ne commence jamais par 0.
  if (national.charAt(0) === '0' && national.length === KLAXO_NATIONAL_LENGTH + 1) {
    national = national.slice(1);
  }

  // 5. Validation finale — c'est le SEUL endroit où l'on refuse.
  if (national.length !== KLAXO_NATIONAL_LENGTH) {
    return fail(national.length < KLAXO_NATIONAL_LENGTH ? 'too_short' : 'too_long');
  }
  if (KLAXO_NATIONAL_PREFIXES.indexOf(national.charAt(0)) === -1) {
    return fail('invalid_prefix');
  }

  return { ok: true, e164: '+212' + national, national: national, reason: null };
}

/**
 * Formatage lisible pour réafficher le numéro dans le champ : +212 6 12 34 56 78.
 * Purement cosmétique — la valeur envoyée reste toujours e164.
 */
function klaxoFormatPhoneDisplay(e164) {
  var m = /^\+212(\d)(\d{2})(\d{2})(\d{2})(\d{2})$/.exec(e164 || '');
  if (!m) return e164 || '';
  return '+212 ' + m[1] + ' ' + m[2] + ' ' + m[3] + ' ' + m[4] + ' ' + m[5];
}

/** Messages destinés au client, en français. Un seul par code d'erreur. */
var KLAXO_PHONE_MESSAGES = {
  empty: 'Entre ton numéro de téléphone.',
  too_short: 'Ce numéro est trop court. Exemple : 06 12 34 56 78.',
  too_long: 'Ce numéro a trop de chiffres. Exemple : 06 12 34 56 78.',
  invalid_prefix: 'Un numéro marocain commence par 05, 06 ou 07.',
  foreign_number: 'On livre uniquement au Maroc. Entre un numéro marocain.',
  not_a_string: 'Entre ton numéro de téléphone.'
};

if (typeof window !== 'undefined') {
  window.KlaxoPhone = {
    normalize: klaxoNormalizePhone,
    format: klaxoFormatPhoneDisplay,
    messages: KLAXO_PHONE_MESSAGES
  };
}

export {
  klaxoNormalizePhone,
  klaxoFormatPhoneDisplay,
  KLAXO_PHONE_MESSAGES
};
