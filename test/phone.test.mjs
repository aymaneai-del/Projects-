import test from 'node:test';
import assert from 'node:assert/strict';
import { klaxoNormalizePhone, klaxoFormatPhoneDisplay } from '../theme/assets/klaxo-phone.js';

/*
 * La règle du projet : on accepte tout ce qu'un client peut raisonnablement
 * taper, on ne refuse que l'impossible. Chaque cas "accepté" ci-dessous est
 * une commande qui serait perdue si la normalisation régressait.
 */

const ACCEPTE = [
  // [saisie, e164 attendu, description]
  ['0612345678',        '+212612345678', 'mobile 06 collé'],
  ['06 12 34 56 78',    '+212612345678', 'mobile 06 avec espaces'],
  ['06-12-34-56-78',    '+212612345678', 'mobile 06 avec tirets'],
  ['06.12.34.56.78',    '+212612345678', 'mobile 06 avec points'],
  ['0712345678',        '+212712345678', 'mobile 07'],
  ['0522334455',        '+212522334455', 'fixe 05 Casablanca'],
  ['05.22.33.44.55',    '+212522334455', 'fixe 05 avec points'],
  ['+212612345678',     '+212612345678', 'international avec +'],
  ['+212 6 12 34 56 78','+212612345678', 'international espacé'],
  ['212612345678',      '+212612345678', 'international sans +'],
  ['00212612345678',    '+212612345678', 'international avec 00'],
  ['612345678',         '+212612345678', 'sans zéro initial'],
  ['  0612345678  ',    '+212612345678', 'espaces autour'],
  ['(06) 12 34 56 78',  '+212612345678', 'parenthèses'],
  ['0612-345-678',      '+212612345678', 'découpage inhabituel'],
  ['+212(0)612345678',  '+212612345678', 'zéro parasite après indicatif'],
];

const REFUSE = [
  ['',                'empty',          'vide'],
  ['   ',             'empty',          'espaces seuls'],
  ['06123456',        'too_short',      'trop court'],
  ['061234567890',    'too_long',       'trop long'],
  ['0112345678',      'invalid_prefix', 'préfixe 01 inexistant au Maroc'],
  ['0912345678',      'invalid_prefix', 'préfixe 09 inexistant au Maroc'],
  ['+33612345678',    'foreign_number', 'numéro français avec +'],
  ['0033612345678',   'foreign_number', 'numéro français avec 00'],
  ['+1 555 010 9999', 'foreign_number', 'numéro américain'],
  ['abcdefgh',        'empty',          'que des lettres'],
];

test('accepte toutes les écritures marocaines courantes', () => {
  for (const [saisie, attendu, desc] of ACCEPTE) {
    const r = klaxoNormalizePhone(saisie);
    assert.equal(r.ok, true, `REJET INATTENDU (${desc}) : "${saisie}" → ${r.reason}`);
    assert.equal(r.e164, attendu, `mauvaise normalisation (${desc}) : "${saisie}"`);
    assert.equal(r.national.length, 9, `national mal découpé (${desc})`);
  }
});

test('refuse ce qui ne peut pas être un numéro marocain', () => {
  for (const [saisie, raison, desc] of REFUSE) {
    const r = klaxoNormalizePhone(saisie);
    assert.equal(r.ok, false, `ACCEPTÉ À TORT (${desc}) : "${saisie}"`);
    assert.equal(r.reason, raison, `mauvais motif (${desc}) : "${saisie}"`);
  }
});

test('la normalisation est idempotente', () => {
  // Un numéro déjà normalisé qui repasse dans la fonction ne doit pas bouger :
  // le formulaire peut normaliser au blur puis re-normaliser à la soumission.
  for (const [saisie] of ACCEPTE) {
    const une = klaxoNormalizePhone(saisie);
    const deux = klaxoNormalizePhone(une.e164);
    assert.equal(deux.ok, true, `2e passage rejeté pour "${saisie}"`);
    assert.equal(deux.e164, une.e164, `2e passage a modifié "${une.e164}"`);
  }
});

test('les entrées non-chaînes ne font pas planter le formulaire', () => {
  for (const v of [null, undefined, 42, {}, [], NaN, true]) {
    const r = klaxoNormalizePhone(v);
    assert.equal(r.ok, false);
    assert.equal(r.reason, 'not_a_string');
  }
});

test('affichage lisible sans altérer la valeur canonique', () => {
  assert.equal(klaxoFormatPhoneDisplay('+212612345678'), '+212 6 12 34 56 78');
  assert.equal(klaxoFormatPhoneDisplay('+212522334455'), '+212 5 22 33 44 55');
  // Entrée inattendue : renvoyer tel quel plutôt que casser le rendu.
  assert.equal(klaxoFormatPhoneDisplay('nawak'), 'nawak');
  assert.equal(klaxoFormatPhoneDisplay(null), '');
});

test('chaque motif de rejet a un message client', async () => {
  const { KLAXO_PHONE_MESSAGES } = await import('../theme/assets/klaxo-phone.js');
  const motifs = new Set(REFUSE.map(([, raison]) => raison));
  motifs.add('not_a_string');
  for (const m of motifs) {
    assert.ok(KLAXO_PHONE_MESSAGES[m], `pas de message pour le motif "${m}"`);
  }
});
