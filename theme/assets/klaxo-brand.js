/*
 * KLAXO — comportements de marque : ombre de l'en-tête et menu mobile.
 *
 * Volontairement minimal. Le JS de l'inspiration animait au survol depuis le
 * script (ce que le CSS fait mieux) et affichait « Ajouté au panier ! » après
 * un délai fixe, sans vérifier que l'ajout avait réussi — un faux succès est
 * pire qu'une absence de retour.
 */

(function () {
  'use strict';

  /* En-tête : ombre au défilement.
     On ne touche au DOM que lorsque l'état CHANGE, pas à chaque pixel défilé. */
  var header = document.querySelector('[data-klaxo-header]');
  if (header) {
    var ombre = false;
    window.addEventListener(
      'scroll',
      function () {
        var doitOmbrer = window.scrollY > 10;
        if (doitOmbrer !== ombre) {
          ombre = doitOmbrer;
          header.classList.toggle('is-scrolled', ombre);
        }
      },
      { passive: true }
    );
  }

  /* Menu mobile, avec l'état annoncé aux lecteurs d'écran. */
  var burger = document.querySelector('[data-klaxo-burger]');
  var nav = document.getElementById('klaxo-nav');

  if (burger && nav) {
    var MOBILE = '(max-width: 860px)';

    var appliquer = function (ouvert) {
      nav.hidden = !ouvert;
      burger.setAttribute('aria-expanded', String(ouvert));
    };

    // Fermé au chargement sur mobile, toujours visible au-delà.
    var mq = window.matchMedia(MOBILE);
    var synchroniser = function () {
      if (mq.matches) {
        appliquer(false);
      } else {
        nav.hidden = false;
        burger.setAttribute('aria-expanded', 'false');
      }
    };
    synchroniser();
    mq.addEventListener('change', synchroniser);

    burger.addEventListener('click', function () {
      appliquer(nav.hidden);
    });

    // Échap ferme le menu et rend le focus au bouton.
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && mq.matches && !nav.hidden) {
        appliquer(false);
        burger.focus();
      }
    });
  }
})();
