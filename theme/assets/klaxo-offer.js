/*
 * KLAXO — comportement de la section offre (Phase 1).
 *
 * Trois responsabilités :
 *   1. Sélection de palier → mise à jour du prix affiché, partout.
 *   2. Barre mobile : visible tant que le formulaire ne l'est pas.
 *   3. Normalisation du téléphone en amélioration progressive sur le formulaire
 *      de l'app COD, et déclenchement d'InitiateCheckout au premier contact réel.
 *
 * Aucune dépendance, aucun secret.
 */

(function () {
  'use strict';

  var root = document.querySelector('[data-klaxo-offer]');
  if (!root) return;

  /* ── 1. Paliers ───────────────────────────────────────────────────────── */

  var radios = Array.prototype.slice.call(root.querySelectorAll('input[name="klaxo_tier"]'));
  var stickyPrice = document.querySelector('[data-klaxo-sticky-price]');

  // Déclaré ici et pas plus bas : syncPrice() s'exécute dès le chargement et a
  // besoin de la zone du formulaire. Déclaré après, `var` le hisserait à
  // undefined au premier appel et la variante ne serait jamais transmise.
  var formZone = root.querySelector('[data-klaxo-order-form]');

  function selectedTier() {
    for (var i = 0; i < radios.length; i++) {
      if (radios[i].checked) return radios[i];
    }
    return radios[0] || null;
  }

  /**
   * Propage la variante choisie partout où le prix facturé se décide.
   *
   * Trois canaux, parce que les apps COD ne lisent pas toutes la même chose :
   *   - l'URL ?variant=  (lue au chargement et par la plupart des apps)
   *   - un input[name="id"] dans la zone du formulaire
   *   - un champ de note pour que le call center voie le pack commandé
   *
   * Sans ça, le client verrait un prix et l'app en encaisserait un autre.
   */
  function syncPrice() {
    var tier = selectedTier();
    if (!tier) return;

    var price = tier.dataset.price;
    var variantId = tier.dataset.variantId;

    root.dataset.selectedPrice = price;
    if (stickyPrice && tier.dataset.priceLabel) {
      stickyPrice.textContent = tier.dataset.priceLabel;
    }

    if (variantId) {
      // L'app lit souvent la variante dans l'URL. replaceState : pas d'entrée
      // supplémentaire dans l'historique, le bouton retour reste utilisable.
      try {
        var url = new URL(window.location.href);
        url.searchParams.set('variant', variantId);
        window.history.replaceState({}, '', url);
      } catch (e) {
        /* URL non manipulable : les deux autres canaux prennent le relais. */
      }

      if (formZone) {
        var champId = formZone.querySelector('input[name="id"], select[name="id"]');
        if (champId) {
          champId.value = variantId;
          // Certaines apps écoutent 'change' pour recalculer leur total.
          champId.dispatchEvent(new Event('change', { bubbles: true }));
        }
      }
    }

    var note = document.querySelector('[name="properties[klaxo_pack]"]');
    if (note) note.value = tier.dataset.label || tier.value;
  }

  radios.forEach(function (radio) {
    radio.addEventListener('change', syncPrice);
  });
  syncPrice();

  /* ── 2. Barre mobile ──────────────────────────────────────────────────── */

  var sticky = document.querySelector('[data-klaxo-sticky]');

  if (sticky && formZone) {
    sticky.hidden = false;

    if ('IntersectionObserver' in window) {
      // Masquer la barre dès que le formulaire est à l'écran : la laisser
      // recouvrirait les champs pendant la saisie, sur des écrans déjà réduits
      // par le clavier virtuel.
      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            sticky.classList.toggle('is-hidden', entry.isIntersecting);
          });
        },
        { threshold: 0.2 }
      );
      observer.observe(formZone);
    }

    var stickyBtn = sticky.querySelector('[data-klaxo-sticky-btn]');
    if (stickyBtn) {
      stickyBtn.addEventListener('click', function () {
        formZone.scrollIntoView({ behavior: 'smooth', block: 'center' });
        var firstField = formZone.querySelector('input, select, textarea');
        if (firstField) {
          // Laisser le défilement se terminer avant de donner le focus, sinon
          // le clavier mobile s'ouvre et interrompt l'animation.
          setTimeout(function () {
            firstField.focus({ preventScroll: true });
          }, 400);
        }
      });
    }
  }

  /* ── 3. Formulaire : téléphone et InitiateCheckout ────────────────────── */

  /**
   * Repère le champ téléphone du formulaire de l'app, quel que soit son nommage.
   * On reste tolérant : rater le champ dégrade la normalisation, mais ne doit
   * jamais empêcher la commande de partir.
   */
  function findPhoneField(scope) {
    return (
      scope.querySelector('input[type="tel"]') ||
      scope.querySelector('input[name*="phone" i]') ||
      scope.querySelector('input[name*="tel" i]') ||
      scope.querySelector('input[autocomplete="tel"]')
    );
  }

  /**
   * Attend que klaxo-phone.js soit disponible.
   *
   * Nécessaire : klaxo-phone.js est chargé en module (il expose un export ESM
   * pour les tests), or les modules s'exécutent APRÈS les scripts `defer` comme
   * celui-ci. Un simple `if (!window.KlaxoPhone) return` désactiverait donc la
   * normalisation en silence — exactement le genre de panne invisible qui coûte
   * des commandes sans laisser de trace.
   */
  function whenPhoneReady(callback) {
    if (window.KlaxoPhone) {
      callback();
      return;
    }
    var waited = 0;
    var timer = setInterval(function () {
      if (window.KlaxoPhone) {
        clearInterval(timer);
        callback();
      } else if ((waited += 50) >= 5000) {
        clearInterval(timer);
        // Le module ne viendra plus. La saisie part telle quelle : dégradé,
        // mais jamais bloquant.
        console.warn('[klaxo] klaxo-phone.js indisponible — normalisation désactivée');
      }
    }, 50);
  }

  /**
   * Normalisation en amélioration progressive.
   *
   * On corrige la saisie au blur pour que le numéro parte en format unique,
   * mais on ne BLOQUE jamais la soumission : l'app a sa propre validation, et
   * un rejet supplémentaire de notre part serait une commande perdue.
   */
  function enhancePhone(field) {
    if (!field || field.dataset.klaxoPhone === '1') return;
    field.dataset.klaxoPhone = '1';

    field.setAttribute('inputmode', 'tel');
    field.setAttribute('autocomplete', 'tel');

    var hint = document.createElement('p');
    hint.className = 'klaxo-phone-hint';
    hint.hidden = true;
    hint.setAttribute('role', 'status');
    field.insertAdjacentElement('afterend', hint);

    field.addEventListener('blur', function () {
      var raw = field.value;
      if (!raw.trim()) {
        hint.hidden = true;
        return;
      }

      var result = window.KlaxoPhone.normalize(raw);
      if (result.ok) {
        field.value = result.e164;
        hint.hidden = true;
        field.removeAttribute('aria-invalid');
      } else {
        // Message d'aide, pas un blocage : la valeur saisie reste intacte.
        hint.textContent = window.KlaxoPhone.messages[result.reason] || '';
        hint.hidden = !hint.textContent;
        field.setAttribute('aria-invalid', 'true');
      }
    });
  }

  function wireForm(scope) {
    var field = findPhoneField(scope);
    if (field) {
      whenPhoneReady(function () {
        enhancePhone(field);
      });
    }

    // InitiateCheckout au premier contact réel avec un champ — pas au chargement.
    // Déclenché à l'affichage, il serait aussi fréquent qu'un ViewContent et
    // n'apporterait aucun signal exploitable.
    scope.addEventListener(
      'focusin',
      function () {
        if (window.KlaxoTrack) {
          window.KlaxoTrack.initiateCheckout({
            currency: 'MAD',
            value: Number(root.dataset.selectedPrice || 0),
            content_ids: [root.dataset.productId || '']
          });
        }
      },
      { once: true }
    );
  }

  if (formZone) {
    if (findPhoneField(formZone)) {
      wireForm(formZone);
    } else {
      // Le formulaire de l'app arrive après le chargement : on l'attend.
      var formObserver = new MutationObserver(function () {
        if (findPhoneField(formZone)) {
          wireForm(formZone);
          formObserver.disconnect();
        }
      });
      formObserver.observe(formZone, { childList: true, subtree: true });
      setTimeout(function () {
        formObserver.disconnect();
      }, 15000);
    }
  }
})();
