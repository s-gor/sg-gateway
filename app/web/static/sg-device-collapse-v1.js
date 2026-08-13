/* SG-Gateway 0.1.0-021.9 — collapsed device cards, clean single-surface V3 */
(() => {
  'use strict';

  const interactiveSelector = 'button, a, input, select, textarea, label, form, details, summary, dialog';
  const protocolOrder = [
    'xray_reality_tcp',
    'xray_xhttp_reality',
    'xray_xhttp_tls',
    'xray_hysteria2',
    'amneziawg',
    'amneziawg3',
    'mihomo',
    'anytls',
    'tuic'
  ];

  function setExpanded(card, button, expanded) {
    card.classList.toggle('sg-device-collapsed', !expanded);
    button.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    button.setAttribute('aria-label', expanded ? 'Свернуть устройство' : 'Развернуть устройство');
    button.title = expanded ? 'Свернуть устройство' : 'Развернуть устройство';
  }

  function deviceCardForDialog(dialog) {
    if (!dialog) return null;
    if (dialog.id === 'dv-edit-client-dialog') {
      return [...document.querySelectorAll('.dv16-device')].find(card =>
        card.querySelector('.dv16-device-kind')?.textContent.trim() === 'ОСНОВНОЕ'
      ) || null;
    }
    const match = /^dv-edit-device-(\d+)$/.exec(dialog.id || '');
    return match ? document.getElementById(`device-${match[1]}`) : null;
  }

  function cardHasProfile(card, title) {
    if (!card) return false;
    return [...card.querySelectorAll('.dv16-profile-tags span')].some(item =>
      item.textContent.trim() === title
    );
  }

  function createAwg3Label(checked, editMode) {
    const label = document.createElement('label');
    label.className = 'dv16-protocol';

    const input = document.createElement('input');
    input.type = 'checkbox';
    input.name = 'protocols';
    input.value = 'amneziawg3';
    input.checked = checked;

    const copy = document.createElement('span');
    const title = document.createElement('strong');
    const note = document.createElement('small');
    title.textContent = 'AmneziaWG 3.0';
    note.textContent = editMode
      ? (checked ? 'Подключён — реквизиты сохранятся' : 'Доступен для добавления')
      : 'UDP 586 · отдельная конфигурация и QR';
    copy.append(title, note);
    label.append(input, copy);
    return label;
  }

  function setLabelTitle(label, title) {
    const target = label?.querySelector('strong');
    if (target) target.textContent = title;
  }

  function setAvailableNote(label, text) {
    const input = label?.querySelector('input[name="protocols"]');
    const note = label?.querySelector('small');
    if (input && note && !input.disabled) note.textContent = text;
  }

  function normalizeProtocolFieldset(fieldset) {
    if (!fieldset || fieldset.dataset.sgProtocolGridReady === '1') return;
    const dialog = fieldset.closest('dialog');
    const addMode = dialog?.id === 'dv46-device-dialog';
    const editMode = dialog?.id === 'dv-edit-client-dialog' || /^dv-edit-device-\d+$/.test(dialog?.id || '');

    if (!fieldset.querySelector('input[name="protocols"][value="amneziawg3"]')) {
      const checked = editMode && cardHasProfile(deviceCardForDialog(dialog), 'AmneziaWG 3.0');
      fieldset.appendChild(createAwg3Label(checked, editMode));
    }

    const byValue = new Map();
    fieldset.querySelectorAll(':scope > label.dv16-protocol').forEach(label => {
      const input = label.querySelector('input[name="protocols"]');
      if (input) byValue.set(input.value, label);
    });

    setLabelTitle(byValue.get('amneziawg'), 'AmneziaWG 2.0');
    setLabelTitle(byValue.get('amneziawg3'), 'AmneziaWG 3.0');

    if (addMode) {
      setAvailableNote(byValue.get('xray_reality_tcp'), 'Отдельный профиль и QR');
      setAvailableNote(byValue.get('xray_xhttp_reality'), 'Отдельный профиль и QR');
      setAvailableNote(byValue.get('xray_xhttp_tls'), 'Отдельный профиль и QR');
      setAvailableNote(byValue.get('xray_hysteria2'), 'Отдельный профиль и QR');
      setAvailableNote(byValue.get('amneziawg'), 'UDP 585 · отдельная конфигурация и QR');
      setAvailableNote(byValue.get('amneziawg3'), 'UDP 586 · отдельная конфигурация и QR');
      setAvailableNote(byValue.get('mihomo'), 'Mieru-ссылка и Mihomo YAML');
      setAvailableNote(byValue.get('anytls'), 'Отдельный TLS-профиль и QR');
      setAvailableNote(byValue.get('tuic'), 'Отдельный QUIC/UDP-профиль и QR');
    }

    protocolOrder.forEach(value => {
      const label = byValue.get(value);
      if (label) fieldset.appendChild(label);
    });

    fieldset.dataset.sgProtocolGridReady = '1';
  }

  function normalizeProtocolPickers() {
    document.querySelectorAll('.dv16-protocol-list').forEach(normalizeProtocolFieldset);

    const addDialog = document.getElementById('dv46-device-dialog');
    const picker = addDialog?.querySelector('.dv16-channel-picker');
    if (picker) picker.open = true;

    const recommended = addDialog?.querySelector('.dv16-recommended span');
    if (recommended) recommended.textContent = 'VLESS Reality TCP, Mieru и персональная SUB.';
  }

  function markWarmActionButtons() {
    document.querySelectorAll('.dv16-device-controls .button').forEach(button => {
      const text = button.textContent.replace(/\s+/g, ' ').trim().toLowerCase();
      if (text.startsWith('отключить')) {
        button.classList.add('sg-warm-action');
      }
    });
  }

  function initDevice(card) {
    if (card.dataset.sgCollapseReady === '1') return;

    const head = card.querySelector(':scope > .dv16-device-head');
    const controls = head?.querySelector('.dv16-device-controls');
    if (!head || !controls) return;

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'button sg-device-collapse-toggle';
    button.innerHTML = '<span aria-hidden="true">⌄</span>';
    controls.appendChild(button);

    card.dataset.sgCollapseReady = '1';
    setExpanded(card, button, false);

    button.addEventListener('click', event => {
      event.preventDefault();
      event.stopPropagation();
      setExpanded(card, button, card.classList.contains('sg-device-collapsed'));
    });

    head.addEventListener('click', event => {
      if (event.target.closest(interactiveSelector)) return;
      setExpanded(card, button, card.classList.contains('sg-device-collapsed'));
    });

    head.addEventListener('keydown', event => {
      if (event.target.closest(interactiveSelector)) return;
      if (event.key !== 'Enter' && event.key !== ' ') return;
      event.preventDefault();
      setExpanded(card, button, card.classList.contains('sg-device-collapsed'));
    });

    const title = head.querySelector('.dv16-device-title');
    if (title) {
      title.tabIndex = 0;
      title.setAttribute('role', 'button');
      title.setAttribute('aria-label', 'Развернуть или свернуть устройство');
    }
  }

  function initAll() {
    normalizeProtocolPickers();
    document.querySelectorAll('.dv16-devices > .dv16-device').forEach(initDevice);
    markWarmActionButtons();

    const hash = String(location.hash || '');
    if (hash.startsWith('#device-')) {
      const target = document.querySelector(hash);
      const button = target?.querySelector('.sg-device-collapse-toggle');
      if (target && button) setExpanded(target, button, true);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll, { once: true });
  } else {
    initAll();
  }
})();
