const NAV_ITEMS = [
  ["Build", null],
  ["Overview", "◫"],
  ["Agents", "◉", "6"],
  ["Knowledge", "▤", "4"],
  ["Deploy", null],
  ["Phone numbers", "☏", "3"],
  ["Campaigns", "➤", "2"],
  ["Integrations", "⧉"],
  ["Monitor", null],
  ["Calls", "≡", "1.2k"],
  ["Analytics", "▥"],
  ["Evals", "✓"],
];

function renderSidebar(activeItem) {
  const items = NAV_ITEMS.map(([label, icon, count]) => {
    if (icon === null) return `<div class="nav-label">${label}</div>`;
    const active = label === activeItem ? " active" : "";
    const badge = count ? `<span class="count">${count}</span>` : "";
    return `<div class="nav-item${active}"><span class="ico">${icon}</span>${label}${badge}</div>`;
  }).join("");
  document.body.insertAdjacentHTML(
    "afterbegin",
    `<aside class="sidebar">
      <div class="logo"><div class="logo-mark">◖</div>Voice Agent Studio</div>
      ${items}
      <div class="sidebar-foot"><div class="avatar">AK</div>
        <div><div style="font-weight:600">Aman Kumar</div><div class="muted" style="font-size:11px">Personal workspace</div></div>
      </div>
    </aside>`
  );
}

if (document.body.dataset.active) renderSidebar(document.body.dataset.active);
