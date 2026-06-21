/* HelpDesk Lite — melhorias progressivas da UI.
 * Sem dependências, sem inline (compatível com a CSP self-only).
 * A aplicação funciona normalmente mesmo sem este script. */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    // Menu de navegação responsivo (mobile).
    var toggle = document.querySelector("[data-nav-toggle]");
    var nav = document.querySelector("[data-nav]");
    if (toggle && nav) {
      toggle.addEventListener("click", function () {
        var open = nav.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
      });
    }

    // Destaca o link de navegação da página atual.
    var path = window.location.pathname;
    document.querySelectorAll(".nav__link").forEach(function (link) {
      var href = link.getAttribute("href");
      if (!href || href === "/") return;
      if (path === href || path.indexOf(href) === 0) {
        link.classList.add("is-active");
      }
    });

    // Auto-oculta mensagens flash de sucesso após alguns segundos.
    document.querySelectorAll(".alert.success").forEach(function (el) {
      window.setTimeout(function () {
        el.style.transition = "opacity .4s ease";
        el.style.opacity = "0";
        window.setTimeout(function () {
          el.remove();
        }, 400);
      }, 4500);
    });
  });
})();
