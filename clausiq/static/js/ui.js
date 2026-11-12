/* Shared UI helpers: icons, escaping, toasts, modals, diffing, charts. */
const UI = (() => {
  const ICONS = {
    shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l8 3.5v5.2c0 5-3.4 8.1-8 9.3-4.6-1.2-8-4.3-8-9.3V6.5L12 3z"/><path d="M9 12l2 2 4-4.5"/></svg>',
    scale: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 4v16M7 7h10M7 7l-3.5 6a3.5 3.5 0 005.9 1.2L12 11l2.6 3.2a3.5 3.5 0 005.9-1.2L17 7"/></svg>',
    dashboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7.5" height="9" rx="1.5"/><rect x="13.5" y="3" width="7.5" height="5.5" rx="1.5"/><rect x="13.5" y="12" width="7.5" height="9" rx="1.5"/><rect x="3" y="15.5" width="7.5" height="5.5" rx="1.5"/></svg>',
    doc: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2.5h8l4 4V21H6z"/><path d="M14 2.5v4h4M9 12h6M9 16h6"/></svg>',
    scan: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7V4h3M18 4h3v3M3 17v3h3M18 20h3v-3"/><path d="M7 12h10M12 7l2 2-2 2M12 17l-2-2 2-2"/></svg>',
    negotiate: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h13l-4-3.5M4 6l4 3.5M20 18H7l4 3.5M20 18l-4-3.5"/><path d="M7 6v10"/></svg>',
    gate: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l8 3.5v5.2c0 5-3.4 8.1-8 9.3-4.6-1.2-8-4.3-8-9.3V6.5L12 3z"/><path d="M8.5 12.2l2.3 2.3 4.7-4.8"/></svg>',
    audit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 6h13M8 12h13M8 18h13"/><circle cx="4" cy="6" r="1" fill="currentColor"/><circle cx="4" cy="12" r="1" fill="currentColor"/><circle cx="4" cy="18" r="1" fill="currentColor"/></svg>',
    book: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4.5A2.5 2.5 0 016.5 2H20v17H6.5A2.5 2.5 0 004 21.5z"/><path d="M4 19.5A2.5 2.5 0 016.5 17H20M9 7h7M9 11h5"/></svg>',
    bug: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 5a4 4 0 018 0v6a4 4 0 01-8 0z"/><path d="M4 8h2M18 8h2M6 20v-3M18 20v-3M12 4v-1M6.5 5L4.5 7M17.5 5l2 2M12 11v4M8 15H4M20 15h-4"/></svg>',
    gear: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3.2"/><path d="M19 12a7 7 0 00-.1-1.2l2-1.5-2-3.4-2.3.9a7 7 0 00-2-1.2L14.3 3h-4l-.3 2.6a7 7 0 00-2 1.2l-2.3-.9-2 3.4 2 1.5a7 7 0 000 2.4l-2 1.5 2 3.4 2.3-.9a7 7 0 002 1.2l.3 2.6h4l.3-2.6a7 7 0 002-1.2l2.3.9 2-3.4-2-1.5a7 7 0 00.1-1.2z"/></svg>',
    logout: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/></svg>',
    upload: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5"/><path d="M4 16v3a2 2 0 002 2h12a2 2 0 002-2v-3"/></svg>',
    play: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 4l13 8-13 8z"/></svg>',
    sparkle: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z"/></svg>',
    robot: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="8" width="16" height="11" rx="2.5"/><path d="M12 4v4M9 13h.01M15 13h.01"/><circle cx="12" cy="16.5" r="1.6"/></svg>',
    user: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="3.6"/><path d="M5 20a7 7 0 0114 0"/></svg>',
    check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
    x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    chev: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 6l6 6-6 6"/></svg>',
    alert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l10 18H2z"/><path d="M12 10v4M12 17.2v.2"/></svg>',
    trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h16M9 7V4h6v3M6.5 7l1 13h9l1-13"/></svg>',
  };

  const icon = (name, cls = "") => `<span class="ic ${cls}">${ICONS[name] || ""}</span>`;
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));

  function toast(message, type = "info", ms = 3600) {
    const root = document.getElementById("toast-root");
    const el = document.createElement("div");
    el.className = "toast " + type;
    el.textContent = message;
    root.appendChild(el);
    setTimeout(() => { el.style.opacity = "0"; el.style.transition = "opacity .3s"; setTimeout(() => el.remove(), 320); }, ms);
  }

  function modal(html) {
    const root = document.getElementById("modal-root");
    root.innerHTML = `<div class="modal-backdrop"></div><div class="modal">${html}</div>`;
    root.classList.add("open");
    root.querySelector(".modal-backdrop").onclick = closeModal;
    root.querySelectorAll("[data-close]").forEach((b) => (b.onclick = closeModal));
    return root.querySelector(".modal");
  }
  function closeModal() {
    const root = document.getElementById("modal-root");
    root.classList.remove("open");
    root.innerHTML = "";
  }

  function timeAgo(ts) {
    if (!ts) return "—";
    const t = new Date(ts.endsWith("Z") ? ts : ts + "Z").getTime();
    if (isNaN(t)) return ts;
    const s = Math.max(0, Math.floor((Date.now() - t) / 1000));
    if (s < 60) return "just now";
    if (s < 3600) return Math.floor(s / 60) + "m ago";
    if (s < 86400) return Math.floor(s / 3600) + "h ago";
    return Math.floor(s / 86400) + "d ago";
  }
  function fmtTime(ts) {
    if (!ts) return "—";
    const t = new Date(ts.endsWith("Z") ? ts : ts + "Z");
    return isNaN(t) ? ts : t.toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  }

  /* Word-level LCS diff producing [{t:"same|del|ins", v:"..."}] */
  function wordDiff(a, b) {
    const A = String(a).split(/(\s+)/).filter(Boolean);
    const B = String(b).split(/(\s+)/).filter(Boolean);
    const n = A.length, m = B.length;
    const dp = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
    for (let i = n - 1; i >= 0; i--) {
      for (let j = m - 1; j >= 0; j--) {
        dp[i][j] = A[i] === B[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
      }
    }
    const out = [];
    let i = 0, j = 0;
    while (i < n && j < m) {
      if (A[i] === B[j]) { out.push({ t: "same", v: A[i] }); i++; j++; }
      else if (dp[i + 1][j] >= dp[i][j + 1]) { out.push({ t: "del", v: A[i++] }); }
      else { out.push({ t: "ins", v: B[j++] }); }
    }
    while (i < n) out.push({ t: "del", v: A[i++] });
    while (j < m) out.push({ t: "ins", v: B[j++] });
    return out;
  }
  const renderDiff = (a, b) =>
    wordDiff(a, b).map((tok) =>
      tok.t === "del" ? `<del>${esc(tok.v)}</del>` : tok.t === "ins" ? `<ins>${esc(tok.v)}</ins>` : esc(tok.v)
    ).join("");

  function donut(segments, size = 132, stroke = 15) {
    const total = Math.max(1, segments.reduce((s, x) => s + x.value, 0));
    const r = (size - stroke) / 2;
    const c = 2 * Math.PI * r;
    let offset = 0;
    let circles = "";
    segments.forEach((seg) => {
      if (seg.value <= 0) return;
      const len = (seg.value / total) * c;
      circles += `<circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none"
        stroke="${seg.color}" stroke-width="${stroke}"
        stroke-dasharray="${len} ${c - len}" stroke-dashoffset="${-offset}"
        transform="rotate(-90 ${size / 2} ${size / 2})" stroke-linecap="butt"/>`;
      offset += len;
    });
    return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="rgba(255,255,255,.05)" stroke-width="${stroke}"/>
      ${circles}
      <text x="50%" y="47%" text-anchor="middle" fill="#f2ecd9" font-family="Georgia,serif" font-size="${size / 6}">${total}</text>
      <text x="50%" y="60%" text-anchor="middle" fill="#66728a" font-size="${size / 15}">clauses</text>
    </svg>`;
  }

  function riskBadge(level, extra = "") {
    const map = { green: ["green", "Compliant"], yellow: ["yellow", "Negotiable"], red: ["red", "High risk"] };
    const [cls, label] = map[level] || ["ghost", level];
    return `<span class="chip ${cls}"><span class="dot-inline ${cls}"></span>${label}${extra ? " " + esc(extra) : ""}</span>`;
  }

  const statusMeta = {
    uploaded: ["ghost", "Uploaded"],
    reviewing: ["gold", "Reviewing"],
    reviewed: ["blue", "Reviewed"],
    negotiating: ["gold", "Negotiating"],
    negotiated: ["blue", "Negotiated"],
    final: ["green", "Final"],
  };
  const statusChip = (status) => {
    const [cls, label] = statusMeta[status] || ["ghost", status];
    return `<span class="chip ${cls}">${label}</span>`;
  };

  return { ICONS, icon, esc, toast, modal, closeModal, timeAgo, fmtTime, wordDiff, renderDiff, donut, riskBadge, statusChip };
})();
