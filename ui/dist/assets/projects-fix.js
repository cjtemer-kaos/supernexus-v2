// Projects Fix — adds activate button to each project card
(() => {
  const API = window.location.origin;

  async function activateProject(name) {
    try {
      const r = await fetch(`${API}/api/projects/activate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project: name })
      });
      const data = await r.json();
      if (data.status === 'ok') {
        // Reload the projects list
        window.location.reload();
      } else {
        alert('Error: ' + (data.error || 'Unknown'));
      }
    } catch (e) {
      alert('Error activating project: ' + e.message);
    }
  }

  function injectButtons() {
    // Find all project cards — they have a "Contexto" button
    const allButtons = document.querySelectorAll('button');
    const contextoButtons = Array.from(allButtons).filter(b => b.textContent.trim() === 'Contexto');

    contextoButtons.forEach(ctxBtn => {
      const card = ctxBtn.closest('[class]');
      if (!card || card.dataset.activateInjected) return;
      card.dataset.activateInjected = '1';

      // Check if this project is already active
      const badge = card.querySelector('span');
      const isActive = badge && badge.textContent.includes('activo');

      if (!isActive) {
        const activateBtn = document.createElement('button');
        activateBtn.textContent = 'Activar';
        activateBtn.className = ctxBtn.className;
        activateBtn.style.marginLeft = '8px';
        activateBtn.style.backgroundColor = '#06b6d4';
        activateBtn.style.color = '#fff';
        activateBtn.style.border = 'none';
        activateBtn.style.borderRadius = '6px';
        activateBtn.style.padding = '4px 12px';
        activateBtn.style.cursor = 'pointer';
        activateBtn.style.fontSize = '12px';
        activateBtn.style.fontWeight = '500';

        // Get project name from the card
        const nameEl = card.querySelector('h3, [class*="font"]');
        const projectName = nameEl ? nameEl.textContent.trim() : '';

        activateBtn.onclick = (e) => {
          e.stopPropagation();
          if (projectName) activateProject(projectName);
        };

        ctxBtn.parentElement.insertBefore(activateBtn, ctxBtn.nextSibling);
      }
    });
  }

  // Run on load and watch for dynamic changes
  const observer = new MutationObserver(() => {
    setTimeout(injectButtons, 200);
  });
  observer.observe(document.body, { childList: true, subtree: true });
  setTimeout(injectButtons, 500);
})();
