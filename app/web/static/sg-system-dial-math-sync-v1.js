(() => {
  "use strict";

  const clamp = (n, lo = 0, hi = 100) => Math.max(lo, Math.min(hi, n));

  function parsePercent(text) {
    const match = String(text || "").replace(",", ".").match(/(-?\d+(?:\.\d+)?)\s*%/);
    if (!match) return null;
    const value = Number(match[1]);
    return Number.isFinite(value) ? clamp(value) : null;
  }

  function formatPercent(value) {
    const rounded = Math.round(value * 10) / 10;
    return `${rounded.toFixed(1)}%`;
  }

  function diskAvailable(card) {
    const node = card?.querySelector(".sv1-donut-center strong");
    return node ? parsePercent(node.textContent) : null;
  }

  /*
   * Disk breakdown originally expresses each row as a share of USED disk.
   * The dial expresses sectors as a share of TOTAL disk.
   *
   * Convert:
   *     row_total_percent = used_total_percent * row_used_share / 100
   *
   * After this conversion:
   * - every Disk row bar uses the same 0..100 TOTAL-disk scale as the dial;
   * - SG-Gateway's green dial sector is exactly the same percentage as its row;
   * - all converted Disk rows together match the occupied dial sector (rounding aside).
   */
  function syncDiskScale() {
    const card = document.querySelector('[data-sg-disk-card="1"]');
    if (!card) return;

    const available = diskAvailable(card);
    if (available === null) return;

    const usedTotal = clamp(100 - available);
    const rows = card.querySelectorAll(".sv1-disk-breakdown .sv1-disk-part");
    let sgGatewayTotal = 0;

    rows.forEach((row) => {
      const percentNode = row.querySelector(".sv1-disk-part-head em");
      const fill = row.querySelector(".sv1-disk-part-track > span");
      if (!percentNode || !fill) return;

      let usedShare;
      if (row.dataset.sgDiskUsedSharePercent !== undefined) {
        usedShare = Number(row.dataset.sgDiskUsedSharePercent);
      } else {
        usedShare = parsePercent(percentNode.textContent);
        if (usedShare === null) return;
        row.dataset.sgDiskUsedSharePercent = String(usedShare);
      }

      if (!Number.isFinite(usedShare)) return;

      const totalPercent = clamp((usedTotal * usedShare) / 100);
      row.dataset.sgDiskTotalPercent = String(totalPercent);

      percentNode.textContent = formatPercent(totalPercent);
      fill.style.width = `${totalPercent}%`;

      if (/SG-Gateway/i.test(row.textContent || "")) {
        sgGatewayTotal = totalPercent;
      }
    });

    card.style.setProperty("--sg-dial-used-percent", String(usedTotal));
    card.style.setProperty("--sg-dial-gateway-percent", String(clamp(sgGatewayTotal, 0, usedTotal)));
  }

  function syncMemoryScale() {
    const card = document.querySelector('[data-sg-memory-card="1"]');
    if (!card) return;

    const availableNode = card.querySelector(".sv1-donut-center strong");
    const available = availableNode ? parsePercent(availableNode.textContent) : null;
    if (available === null) return;

    const usedTotal = clamp(100 - available);
    let sgGatewayTotal = 0;

    card.querySelectorAll(".sv1-memory-legend .sv1-legend-row").forEach((row) => {
      if (!/SG-Gateway/i.test(row.textContent || "")) return;
      const percentNode = row.querySelector("em");
      const pct = percentNode ? parsePercent(percentNode.textContent) : null;
      if (pct !== null) sgGatewayTotal = pct;
    });

    card.style.setProperty("--sg-dial-used-percent", String(usedTotal));
    card.style.setProperty("--sg-dial-gateway-percent", String(clamp(sgGatewayTotal, 0, usedTotal)));
  }

  function cpuLoad(card) {
    const hero = card?.querySelector(".sv1-cpu-hero");
    if (hero) {
      const raw = getComputedStyle(hero).getPropertyValue("--sg-cpu-percent").trim();
      const n = Number(raw);
      if (Number.isFinite(n)) return clamp(n);
    }

    const aria = card?.querySelector(".sv1-cpu-dial")?.getAttribute("aria-label") || "";
    const fromAria = parsePercent(aria);
    if (fromAria !== null) return fromAria;

    const center = card?.querySelector(".sv1-cpu-dial strong");
    return center ? parsePercent(center.textContent) : null;
  }

  function syncCpuScale() {
    const card = document.querySelector('[data-sg-cpu-card="1"]');
    if (!card) return;

    const usedTotal = cpuLoad(card);
    if (usedTotal === null) return;

    let sgGatewayTotal = 0;
    card.querySelectorAll(".sv1-cpu-breakdown .sv1-cpu-part").forEach((row) => {
      if (!/SG-Gateway/i.test(row.textContent || "")) return;
      const percentNode = row.querySelector(".sv1-cpu-part-head em");
      const pct = percentNode ? parsePercent(percentNode.textContent) : null;
      if (pct !== null) sgGatewayTotal = pct;
    });

    card.style.setProperty("--sg-dial-used-percent", String(usedTotal));
    card.style.setProperty("--sg-dial-gateway-percent", String(clamp(sgGatewayTotal, 0, usedTotal)));
  }

  function syncAll() {
    syncMemoryScale();
    syncDiskScale();
    syncCpuScale();
  }

  let scheduled = false;
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      syncAll();
    });
  }

  document.addEventListener("DOMContentLoaded", syncAll);

  new MutationObserver(schedule).observe(document.documentElement, {
    childList: true,
    subtree: true,
    characterData: true,
  });
})();
