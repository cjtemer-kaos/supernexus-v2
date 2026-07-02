/**
 * graph-fix.js — Inyecta card "Grafo de Arquitectura" en Cerebro
 * Se inserta después de los tabs, antes de las stats cards
 */
(function () {
  "use strict";

  const GRAPH_URL = "/graph";
  let injected = false;

  function injectGraphSection() {
    if (injected) return;
    if (document.getElementById("nexus-graph-card")) return;

    // Find the Brain heading
    const headings = document.querySelectorAll("h1");
    let brainH1 = null;
    for (const h of headings) {
      if (h.textContent && h.textContent.includes("Cerebro")) {
        brainH1 = h;
        break;
      }
    }
    if (!brainH1) return;

    // Find the tab bar — it contains buttons/links like "Dashboard", "Conocimiento", etc.
    // The tab bar is a flex container with border-b
    let tabBar = null;
    const allFlexes = document.querySelectorAll("div.flex");
    for (const el of allFlexes) {
      if (el.textContent.includes("Dashboard") && el.textContent.includes("Conocimiento") &&
          el.className && el.className.includes("border-b")) {
        tabBar = el;
        break;
      }
    }
    if (!tabBar) return;

    // The section container is the tabBar's parent
    const section = tabBar.parentElement;
    if (!section) return;

    // Don't inject twice
    if (section.querySelector("#nexus-graph-card")) {
      injected = true;
      return;
    }

    // Build the card
    const card = document.createElement("div");
    card.id = "nexus-graph-card";
    card.style.cssText = "background:var(--color-nexus-surface);border:1px solid var(--color-nexus-border);border-radius:12px;overflow:hidden;margin:12px 0;";
    card.innerHTML =
      '<div style="display:flex;align-items:center;gap:14px;padding:18px 20px;cursor:pointer;user-select:none;" id="nexus-graph-toggle">' +
        '<div style="width:44px;height:44px;border-radius:12px;background:linear-gradient(135deg,#06b6d4,#8b5cf6);display:flex;align-items:center;justify-content:center;flex-shrink:0;">' +
          '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
            '<circle cx="12" cy="5" r="3"/><circle cx="5" cy="19" r="3"/><circle cx="19" cy="19" r="3"/>' +
            '<line x1="12" y1="8" x2="5" y2="16"/><line x1="12" y1="8" x2="19" y2="16"/>' +
          '</svg>' +
        '</div>' +
        '<div style="flex:1;min-width:0;">' +
          '<div style="font-size:15px;font-weight:700;color:var(--color-nexus-text);margin-bottom:3px;">Grafo de Arquitectura</div>' +
          '<div style="font-size:12px;color:var(--color-nexus-muted);line-height:1.4;">Explora visualmente cómo se conectan los <b>461 archivos</b> y <b>454 relaciones</b> del sistema</div>' +
        '</div>' +
        '<a href="' + GRAPH_URL + '" target="_blank" rel="noreferrer" ' +
           'onclick="event.stopPropagation()" ' +
           'style="padding:10px 20px;border-radius:10px;background:var(--color-nexus-accent);color:white;font-size:13px;font-weight:600;text-decoration:none;white-space:nowrap;display:flex;align-items:center;gap:8px;box-shadow:0 2px 8px rgba(6,182,212,0.3);">' +
          'Abrir grafo' +
          '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">' +
            '<line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/>' +
          '</svg>' +
        '</a>' +
      '</div>' +
      '<div id="nexus-graph-preview" style="display:none;border-top:1px solid var(--color-nexus-border);">' +
        '<iframe src="' + GRAPH_URL + '" style="width:100%;height:450px;border:none;background:#0a0a0f;" loading="lazy"></iframe>' +
      '</div>';

    // Insert after the tab bar
    tabBar.insertAdjacentElement("afterend", card);

    // Toggle preview
    var toggle = document.getElementById("nexus-graph-toggle");
    var preview = document.getElementById("nexus-graph-preview");
    if (toggle && preview) {
      toggle.addEventListener("click", function (e) {
        if (e.target.closest("a")) return;
        preview.style.display = preview.style.display === "none" ? "block" : "none";
      });
    }

    injected = true;
    console.log("[graph-fix] Grafo de Arquitectura inyectado en Cerebro");
  }

  // Try immediately
  injectGraphSection();

  // Watch for DOM changes
  var observer = new MutationObserver(function () {
    if (!injected) injectGraphSection();
  });
  observer.observe(document.body, { childList: true, subtree: true });

  // Retry on navigation
  var lastUrl = location.href;
  setInterval(function () {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      injected = false;
      setTimeout(injectGraphSection, 500);
    }
  }, 1000);
})();
