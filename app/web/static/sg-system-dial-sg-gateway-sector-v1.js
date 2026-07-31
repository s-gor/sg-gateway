(() => {
  "use strict";

  const clamp = (n, lo = 0, hi = 100) => Math.max(lo, Math.min(hi, n));

  function parsePercent(text) {
    const m = String(text || '').replace(',', '.').match(/(-?\d+(?:\.\d+)?)\s*%/);
    if (!m) return null;
    const n = Number(m[1]);
    return Number.isFinite(n) ? clamp(n) : null;
  }

  function rowPercent(container, rowSelector) {
    if (!container) return 0;
    const rows = container.querySelectorAll(rowSelector);
    for (const row of rows) {
      if (!/SG-Gateway/i.test(row.textContent || '')) continue;
      const percentNode = row.querySelector('em');
      const pct = parsePercent(percentNode ? percentNode.textContent : row.textContent);
      return pct === null ? 0 : pct;
    }
    return 0;
  }

  function availableFromDial(card) {
    const strong = card && card.querySelector('.sv1-donut-center strong');
    return strong ? parsePercent(strong.textContent) : null;
  }

  function cpuLoad(card) {
    if (!card) return null;
    const hero = card.querySelector('.sv1-cpu-hero');
    if (hero) {
      const raw = getComputedStyle(hero).getPropertyValue('--sg-cpu-percent').trim();
      const n = Number(raw);
      if (Number.isFinite(n)) return clamp(n);
    }
    const aria = card.querySelector('.sv1-cpu-dial')?.getAttribute('aria-label') || '';
    const fromAria = parsePercent(aria);
    if (fromAria !== null) return fromAria;
    const first = card.querySelector('.sv1-cpu-part-head em');
    return first ? parsePercent(first.textContent) : null;
  }

  function applyMemory() {
    const card = document.querySelector('[data-sg-memory-card="1"]');
    if (!card) return;
    const available = availableFromDial(card);
    if (available === null) return;
    const used = clamp(100 - available);
    const sg = clamp(rowPercent(card, '.sv1-memory-legend .sv1-legend-row'), 0, used);
    card.style.setProperty('--sg-dial-used-percent', String(used));
    card.style.setProperty('--sg-dial-gateway-percent', String(sg));
  }

  function applyDisk() {
    const card = document.querySelector('[data-sg-disk-card="1"]');
    if (!card) return;
    const available = availableFromDial(card);
    if (available === null) return;
    const used = clamp(100 - available);
    const sg = clamp(rowPercent(card, '.sv1-disk-breakdown .sv1-disk-part'), 0, used);
    card.style.setProperty('--sg-dial-used-percent', String(used));
    card.style.setProperty('--sg-dial-gateway-percent', String(sg));
  }

  function applyCpu() {
    const card = document.querySelector('[data-sg-cpu-card="1"]');
    if (!card) return;
    const usedRaw = cpuLoad(card);
    if (usedRaw === null) return;
    const used = clamp(usedRaw);
    const sg = clamp(rowPercent(card, '.sv1-cpu-breakdown .sv1-cpu-part'), 0, used);
    card.style.setProperty('--sg-dial-used-percent', String(used));
    card.style.setProperty('--sg-dial-gateway-percent', String(sg));
  }

  function applyAll() {
    applyMemory();
    applyDisk();
    applyCpu();
  }

  let scheduled = false;
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      applyAll();
    });
  }

  document.addEventListener('DOMContentLoaded', applyAll);
  new MutationObserver(schedule).observe(document.documentElement, {
    childList: true,
    subtree: true,
    characterData: true,
  });
})();
