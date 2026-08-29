/*
 * KLAXO — pont de tracking navigateur (Phase 2, côté thème).
 *
 * Rôle : générer les event_id, capturer l'attribution, déclencher les pixels
 * et relayer vers le Worker. Aucun secret ici — ce fichier est public.
 *
 * Déduplication : le MÊME event_id part vers le pixel navigateur et vers le
 * Worker. Meta et TikTok rapprochent les deux et ne comptent qu'une conversion.
 *
 * Purchase n'est PAS déclenché ici : il vient du webhook Shopify, signé.
 * Ce fichier se contente de déposer l'event_id dans le formulaire pour que la
 * commande le transporte jusqu'au webhook.
 */

(function () {
  'use strict';

  var config = window.KLAXO_CONFIG || {};
  var WORKER = config.workerUrl || '';
  var STORAGE_KEY = 'klaxo_attribution';

  /* ── Identifiants d'événement ─────────────────────────────────────────── */

  function newEventId() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    // Repli pour les navigateurs sans randomUUID : suffisant pour dédupliquer,
    // qui ne demande que l'unicité, pas de l'imprévisibilité cryptographique.
    return 'ev-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
  }

  /* ── Attribution ──────────────────────────────────────────────────────── */

  function readCookie(name) {
    var match = document.cookie.match(new RegExp('(^|;\\s*)' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[2]) : null;
  }

  /**
   * Capture UTM et identifiants de clic à la première visite, puis les conserve.
   *
   * Le stockage est indispensable : le client arrive par une pub, navigue, et
   * commande plusieurs minutes plus tard. Sans persistance, l'attribution serait
   * perdue et la créative responsable de la vente resterait inconnue — or c'est
   * exactement sur cette donnée que se fait le tri manuel des créatives.
   */
  function captureAttribution() {
    var stored = {};
    try {
      stored = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '{}');
    } catch (e) {
      stored = {};
    }

    var params = new URLSearchParams(window.location.search);
    var keys = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'];

    keys.forEach(function (key) {
      var value = params.get(key);
      // Première valeur gagnante : ne pas écraser l'origine réelle si le client
      // revient plus tard par un autre canal.
      if (value && !stored[key]) stored[key] = value;
    });

    var ttclid = params.get('ttclid');
    if (ttclid && !stored.ttclid) stored.ttclid = ttclid;

    if (!stored.landing_url) stored.landing_url = window.location.href;

    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
    } catch (e) {
      // Navigation privée ou stockage bloqué : l'attribution de cette session
      // sera incomplète, mais la commande doit passer quand même.
    }

    return stored;
  }

  var attribution = captureAttribution();

  function currentIdentifiers() {
    return {
      fbp: readCookie('_fbp'),
      fbc: readCookie('_fbc'),
      ttp: readCookie('_ttp'),
      ttclid: attribution.ttclid || null
    };
  }

  /* ── Envoi ────────────────────────────────────────────────────────────── */

  function toWorker(eventName, eventId, custom) {
    if (!WORKER) return;

    var ids = currentIdentifiers();
    var payload = JSON.stringify({
      event_name: eventName,
      event_id: eventId,
      url: window.location.href,
      user: { city: null, fbp: ids.fbp, fbc: ids.fbc, ttp: ids.ttp, ttclid: ids.ttclid },
      custom: custom || {}
    });

    // keepalive : l'envoi survit à la navigation si le client clique juste après.
    try {
      fetch(WORKER + '/collect', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: payload,
        keepalive: true,
        mode: 'cors'
      }).catch(function () {
        // Un échec de mesure ne doit jamais interrompre le parcours d'achat.
      });
    } catch (e) {
      /* idem */
    }
  }

  /**
   * Déclenche un événement sur les pixels ET le Worker, avec le même event_id.
   */
  function track(eventName, custom) {
    var eventId = newEventId();

    if (typeof window.fbq === 'function') {
      window.fbq('track', eventName, custom || {}, { eventID: eventId });
    }
    if (typeof window.ttq === 'object' && window.ttq && typeof window.ttq.track === 'function') {
      window.ttq.track(eventName, custom || {}, { event_id: eventId });
    }

    toWorker(eventName, eventId, custom);
    return eventId;
  }

  /* ── Câblage du formulaire ────────────────────────────────────────────── */

  /**
   * Dépose l'attribution et l'event_id du Purchase dans des champs cachés.
   *
   * Ces champs deviennent des note_attributes de la commande Shopify, que le
   * webhook relit pour dédupliquer le Purchase et rattacher la vente à sa
   * créative. C'est le chaînon qui relie la pub à la commande livrée.
   */
  function primeOrderForm(form) {
    if (!form || form.dataset.klaxoPrimed === '1') return;
    form.dataset.klaxoPrimed = '1';

    var ids = currentIdentifiers();
    var fields = {
      klaxo_event_id: newEventId(),
      klaxo_landing_url: attribution.landing_url || window.location.href,
      klaxo_utm_source: attribution.utm_source || '',
      klaxo_utm_medium: attribution.utm_medium || '',
      klaxo_utm_campaign: attribution.utm_campaign || '',
      klaxo_utm_content: attribution.utm_content || '',
      klaxo_fbp: ids.fbp || '',
      klaxo_fbc: ids.fbc || '',
      klaxo_ttp: ids.ttp || '',
      klaxo_ttclid: ids.ttclid || ''
    };

    Object.keys(fields).forEach(function (name) {
      var existing = form.querySelector('[name="properties[' + name + ']"]');
      if (existing) {
        existing.value = fields[name];
        return;
      }
      var input = document.createElement('input');
      input.type = 'hidden';
      // Convention Shopify : properties[...] devient une note_attribute.
      input.name = 'properties[' + name + ']';
      input.value = fields[name];
      form.appendChild(input);
    });
  }

  /* ── API publique ─────────────────────────────────────────────────────── */

  window.KlaxoTrack = {
    track: track,
    newEventId: newEventId,
    attribution: attribution,
    primeOrderForm: primeOrderForm,

    /** Appelé une fois au chargement de la page produit. */
    viewContent: function (custom) {
      return track('ViewContent', custom);
    },

    /**
     * Appelé au PREMIER contact réel avec le formulaire, pas au chargement.
     * Un InitiateCheckout déclenché à l'affichage n'aurait aucune valeur de
     * signal : il serait aussi fréquent qu'un ViewContent.
     */
    initiateCheckout: (function () {
      var fired = false;
      return function (custom) {
        if (fired) return null;
        fired = true;
        return track('InitiateCheckout', custom);
      };
    })()
  };

  /* ── Démarrage ────────────────────────────────────────────────────────── */

  function boot() {
    var root = document.querySelector('[data-klaxo-offer]');
    if (!root) return;

    window.KlaxoTrack.viewContent({
      content_type: 'product',
      content_ids: [root.dataset.productId || ''],
      currency: 'MAD',
      value: Number(root.dataset.selectedPrice || 0)
    });

    // Le formulaire de l'app COD est injecté après le chargement : on l'attend
    // plutôt que de supposer qu'il est déjà là.
    var attach = function () {
      var form = document.querySelector('[data-klaxo-order-form] form, form[data-klaxo-order-form]');
      if (form) primeOrderForm(form);
      return Boolean(form);
    };

    if (!attach()) {
      var observer = new MutationObserver(function () {
        if (attach()) observer.disconnect();
      });
      observer.observe(document.body, { childList: true, subtree: true });
      // Ne pas observer le DOM indéfiniment : au-delà de 15 s, l'app ne viendra plus.
      setTimeout(function () {
        observer.disconnect();
      }, 15000);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
