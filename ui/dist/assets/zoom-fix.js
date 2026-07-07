/**
 * zoom-fix.js — Zoom controls via Electron IPC bridge
 */
(function() {
  let injected = false;
  let currentZoom = 100;

  function getAPI() {
    return (typeof window !== 'undefined' && window.electronAPI) ? window.electronAPI : null;
  }

  async function zoomIn() {
    const api = getAPI();
    if (api?.zoomIn) {
      const factor = await api.zoomIn();
      currentZoom = Math.round(factor * 100);
    }
    updateDisplay();
  }

  async function zoomOut() {
    const api = getAPI();
    if (api?.zoomOut) {
      const factor = await api.zoomOut();
      currentZoom = Math.round(factor * 100);
    }
    updateDisplay();
  }

  async function zoomReset() {
    const api = getAPI();
    if (api?.zoomReset) {
      await api.zoomReset();
      currentZoom = 100;
    }
    updateDisplay();
  }

  function updateDisplay() {
    const el = document.getElementById('zoom-level-display');
    if (el) el.textContent = currentZoom + '%';
  }

  function createIcon(paths) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', '14');
    svg.setAttribute('height', '14');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    paths.forEach(([tag, attrs]) => {
      const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
      Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
      svg.appendChild(el);
    });
    return svg;
  }

  function inject() {
    if (injected) return;
    const sidebar = document.querySelector('aside');
    if (!sidebar) return;
    if (document.getElementById('zoom-controls-container')) return;

    const container = document.createElement('div');
    container.id = 'zoom-controls-container';
    container.className = 'flex items-center gap-1 px-2 py-2 border-t border-[#2a2a3a] mt-auto';

    // Zoom out
    const outBtn = document.createElement('button');
    outBtn.className = 'p-1.5 rounded-md hover:bg-[#2a2a3a] text-[#a0a0b0] transition-colors';
    outBtn.title = 'Zoom Out (Ctrl+-)';
    outBtn.appendChild(createIcon([
      ['circle', { cx: '11', cy: '11', r: '8' }],
      ['line', { x1: '21', x2: '16.65', y1: '21', y2: '16.65' }],
      ['line', { x1: '8', x2: '14', y1: '11', y2: '11' }]
    ]));
    outBtn.onclick = zoomOut;
    container.appendChild(outBtn);

    // Percentage
    const display = document.createElement('button');
    display.id = 'zoom-level-display';
    display.className = 'flex-1 text-center text-[10px] font-mono text-[#a0a0b0] hover:text-white transition-colors cursor-pointer';
    display.textContent = currentZoom + '%';
    display.title = 'Reset zoom (Ctrl+0)';
    display.onclick = zoomReset;
    container.appendChild(display);

    // Zoom in
    const inBtn = document.createElement('button');
    inBtn.className = 'p-1.5 rounded-md hover:bg-[#2a2a3a] text-[#a0a0b0] transition-colors';
    inBtn.title = 'Zoom In (Ctrl+=)';
    inBtn.appendChild(createIcon([
      ['circle', { cx: '11', cy: '11', r: '8' }],
      ['line', { x1: '21', x2: '16.65', y1: '21', y2: '16.65' }],
      ['line', { x1: '11', x2: '11', y1: '8', y2: '14' }],
      ['line', { x1: '8', x2: '14', y1: '11', y2: '11' }]
    ]));
    inBtn.onclick = zoomIn;
    container.appendChild(inBtn);

    sidebar.appendChild(container);
    injected = true;
    console.log('[zoom-fix] Controls injected');

    // Listen for zoom changes from keyboard shortcuts
    const api = getAPI();
    if (api?.onZoomChanged) {
      api.onZoomChanged((factor) => {
        currentZoom = Math.round(factor * 100);
        updateDisplay();
      });
    }
  }

  new MutationObserver(() => { if (!injected) inject(); })
    .observe(document.body, { childList: true, subtree: true });
  inject();
})();
