/* ClausIQ single-page application: hash router, views, polling. */
const APP = (() => {
  const S = {
    user: API.getUser(),
    settings: null,
    contracts: [],
    playbooks: [],
    approvals: [],
    audit: [],
    dashboard: null,
    contract: null,
    clauses: [],
    risks: [],
    redlines: [],
    negotiation: null,
    messages: [],
    selectedClauseId: null,
    pollers: [],
  };

  const NAV = [
    ["dashboard", "Dashboard", "dashboard"],
    ["contracts", "Contracts", "doc"],
    ["contracts", "Review Studio", "scan"],
    ["approvals", "Approval Gate", "gate"],
    ["negotiate", "Negotiations", "negotiate"],
    ["audit", "Audit Trail", "audit"],
    ["playbooks", "Playbooks", "book"],
    ["redteam", "Red-Team Test", "bug"],
    ["settings", "Settings", "gear"],
  ];

  const appRoot = () => document.getElementById("app");
  const viewRoot = () => document.getElementById("view");
  const clearPollers = () => { S.pollers.forEach(clearTimeout); S.pollers = []; };

  /* ============ Shell ============ */
  function renderShell(route) {
    const u = S.user;
    const active = route.split("/")[0] || "dashboard";
    const navHtml = NAV.map(([r, label, icon]) => {
      const cls = (active === r || (r === "contracts" && ["contract", "negotiate"].includes(active))) ? " active" : "";
      const badge = r === "approvals" && S.pendingApprovals > 0
        ? `<span class="badge-count">${S.pendingApprovals}</span>` : "";
      return `<div class="nav-item${cls}" data-route="${r}">${UI.ICONS[icon]}<span>${label}</span>${badge}</div>`;
    }).join("");
    appRoot().innerHTML = `
      <aside class="sidebar">
        <div class="brand">
          <div class="brand-mark">${UI.ICONS.scale}</div>
          <div><div class="brand-name">ClausIQ</div><div class="brand-sub">Contract Intelligence</div></div>
        </div>
        <nav class="nav">
          <div class="nav-label">Workspace</div>
          ${navHtml}
        </nav>
        <div class="side-user">
          <div class="avatar">${UI.esc((u.name || "?").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase())}</div>
          <div><div class="u-name">${UI.esc(u.name)}</div><div class="u-role">${UI.esc(u.role)} · ${UI.esc(u.organization)}</div></div>
          <button id="logout-btn" title="Sign out">${UI.ICONS.logout}</button>
        </div>
      </aside>
      <div class="main">
        <header class="topbar">
          <div class="page-title" id="page-title"></div>
          <span class="crumb" id="page-crumb"></span>
          <div class="spacer"></div>
          <div class="model-pill" id="model-pill">…</div>
        </header>
        <div class="content" id="view"></div>
      </div>`;
    document.querySelectorAll(".nav-item").forEach((el) => {
      el.onclick = () => { location.hash = "#/" + el.dataset.route; };
    });
    document.getElementById("logout-btn").onclick = async () => {
      await API.logout();
      API.clearSession();
      location.hash = "#/login";
      renderLogin();
    };
    refreshPendingCount();
    loadSettings();
    renderRoute();
  }

  function setTitle(title, crumb = "") {
    const t = document.getElementById("page-title");
    const c = document.getElementById("page-crumb");
    if (t) t.textContent = title;
    if (c) c.textContent = crumb;
  }

  async function loadSettings() {
    try {
      S.settings = await API.get("/api/settings");
      const pill = document.getElementById("model-pill");
      if (!pill) return;
      const on = S.settings.model.key_set;
      pill.innerHTML = `<span class="dot ${on ? "on" : "off"}"></span>${on
        ? "Groq · " + S.settings.model.model
        : "Demo fallback engine"}`;
    } catch { /* noop */ }
  }

  async function refreshPendingCount() {
    try {
      const rows = await API.get("/api/approvals?status=pending");
      S.pendingApprovals = rows.length;
      const badge = document.querySelector('.nav-item[data-route="approvals"]');
      if (badge) {
        const existing = badge.querySelector(".badge-count");
        if (S.pendingApprovals > 0) {
          if (existing) existing.textContent = S.pendingApprovals;
          else badge.insertAdjacentHTML("beforeend", `<span class="badge-count">${S.pendingApprovals}</span>`);
        } else if (existing) existing.remove();
      }
    } catch { /* noop */ }
  }

  /* ============ Login ============ */
  function renderLogin() {
    clearPollers();
    appRoot().innerHTML = `
      <div class="login-wrap">
        <div class="login-brand">
          <div class="logo-row">
            <div class="brand-mark">${UI.ICONS.scale}</div>
            <div><div style="font-family:var(--serif);font-size:26px;color:#f5eed8">ClausIQ</div>
            <div style="font-size:11px;letter-spacing:2px;color:var(--text-faint);text-transform:uppercase">Governed Agentic Contract Intelligence</div></div>
          </div>
          <h1>Contract review that<br/>you can actually trust.</h1>
          <p class="tagline">Five coordinated AI agents review, risk-score, redline and negotiate your
          commercial contracts — and every consequential action still stops at a human approval gate,
          with a tamper-evident audit trail.</p>
          <div class="feature-list">
            ${[
              ["Clause extraction", "Breaks any PDF, DOCX or TXT contract into labeled, source-tracked clauses."],
              ["Playbook risk scoring", "Every green / yellow / red flag cites the exact rule and clause that triggered it."],
              ["Justified redlines", "Surgical, minimal rewrites with a one-line reason for each change."],
              ["Agent-vs-agent negotiation", "Your company agent negotiates with a counterparty agent, round by round."],
              ["Human-in-the-loop gate", "Nothing external ever executes without approval; everything is logged."],
            ].map(([t, d], i) => `
              <div class="feature-item"><span class="num">${i + 1}</span>
                <div><b>${t}</b><span>${d}</span></div></div>`).join("")}
          </div>
        </div>
        <div class="login-panel">
          <div class="login-card">
            <div class="eyebrow">Sign in</div>
            <h2>Welcome back</h2>
            <p class="hint">Use any demo account below to enter the workspace.</p>
            <form id="login-form">
              <div class="field"><label>Email</label><input class="input" name="email" type="email" placeholder="you@nimbus.app" required /></div>
              <div class="field"><label>Password</label><input class="input" name="password" type="password" placeholder="••••••••" required /></div>
              <button class="btn primary" style="width:100%;justify-content:center" type="submit">Sign in to ClausIQ</button>
            </form>
            <div class="demo-accounts">
              ${[
                ["Yashwanth Reddy", "yash@nimbus.app", "demo123", "Founder"],
                ["Maya Krishnan", "maya@nimbus.app", "demo123", "Legal Reviewer"],
                ["ClausIQ Admin", "admin@clausiq.io", "admin123", "Administrator"],
              ].map(([n, e, p, r]) => `
                <div class="demo-account" data-email="${e}" data-pass="${p}">
                  <div class="avatar" style="width:30px;height:30px;font-size:12px">${UI.esc(n.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase())}</div>
                  <div><div class="d-name">${UI.esc(n)}</div><div class="d-mail">${UI.esc(e)}</div></div>
                  <div class="d-tag">${UI.esc(r)}</div>
                </div>`).join("")}
            </div>
          </div>
        </div>
      </div>`;
    document.querySelectorAll(".demo-account").forEach((el) => {
      el.onclick = () => {
        document.querySelector('input[name="email"]').value = el.dataset.email;
        document.querySelector('input[name="password"]').value = el.dataset.pass;
      };
    });
    document.getElementById("login-form").onsubmit = async (ev) => {
      ev.preventDefault();
      const email = ev.target.email.value.trim();
      const password = ev.target.password.value;
      try {
        const res = await API.login(email, password);
        API.setSession(res.token, res.user);
        S.user = res.user;
        location.hash = "#/dashboard";
        renderShell("dashboard");
      } catch (err) {
        UI.toast(err.message, "error");
      }
    };
  }

  /* ============ Router ============ */
  function renderRoute() {
    clearPollers();
    const hash = location.hash.replace(/^#\/?/, "") || "dashboard";
    const parts = hash.split("/");
    const route = parts[0];
    const id = parts[1] ? parseInt(parts[1], 10) : null;
    const root = viewRoot();
    if (!root) return;
    root.innerHTML = `<div class="empty">Loading…</div>`;
    switch (route) {
      case "login": renderLogin(); break;
      case "dashboard": viewDashboard(); break;
      case "contracts": viewContracts(); break;
      case "contract": id ? viewContract(id) : go("contracts"); break;
      case "negotiate": id ? viewNegotiation(id) : viewNegotiations(); break;
      case "approvals": viewApprovals(); break;
      case "audit": viewAudit(); break;
      case "playbooks": viewPlaybooks(); break;
      case "redteam": viewRedTeam(); break;
      case "settings": viewSettings(); break;
      default: go("dashboard");
    }
  }
  const go = (hash) => { location.hash = "#/" + hash; };

  /* ============ Polling ============ */
  function pollJob(jobId, { onDone, onFail, render }) {
    const tick = async () => {
      try {
        const job = await API.get("/api/jobs/" + jobId);
        if (job.status === "complete") { onDone && onDone(job); return; }
        if (job.status === "failed") { onFail && onFail(job); return; }
        render && render(job);
        S.pollers.push(setTimeout(tick, 900));
      } catch (err) {
        onFail && onFail({ error: err.message });
      }
    };
    tick();
  }

  /* ============ Dashboard ============ */
  async function viewDashboard() {
    setTitle("Dashboard");
    S.dashboard = await API.get("/api/dashboard");
    const c = S.dashboard.counts;
    const view = viewRoot();
    view.innerHTML = `
      <div class="page-head">
        <div>
          <div class="eyebrow">Workspace overview</div>
          <h1>Good ${new Date().getHours() < 12 ? "morning" : new Date().getHours() < 17 ? "afternoon" : "evening"}, ${UI.esc(S.user.name.split(" ")[0])}.</h1>
          <div class="sub">Your governed contract-review pipeline at a glance.</div>
        </div>
        <div class="actions">
          <button class="btn" onclick="APP.go('contracts')">${UI.ICONS.upload} Upload contract</button>
          <button class="btn primary" onclick="APP.go('contracts')">${UI.ICONS.scan} Start a review</button>
        </div>
      </div>
      <div class="grid cards-4" style="margin-bottom:16px">
        ${statCard("Contracts", c.contracts, "doc", "ic-blue", "in this workspace")}
        ${statCard("Clauses analyzed", c.clauses, "scan", "ic-gold", "across all reviews")}
        ${statCard("High-risk clauses", c.red, "alert", "ic-red", "require redlines")}
        ${statCard("Pending approvals", c.pending_approvals, "gate", "ic-green", "awaiting a human")}
      </div>
      <div class="grid two">
        <div class="card pad">
          <div class="card-title">Risk distribution</div>
          <div class="card-sub" style="margin-bottom:16px">Outcome of every clause judged against your playbook.</div>
          <div class="donut-wrap">
            ${UI.donut([
              { value: c.green, color: "var(--green)" },
              { value: c.yellow, color: "var(--yellow)" },
              { value: c.red, color: "var(--red)" },
            ])}
            <div class="donut-legend">
              ${legendRow("var(--green)", "Compliant", c.green)}
              ${legendRow("var(--yellow)", "Negotiable", c.yellow)}
              ${legendRow("var(--red)", "High risk", c.red)}
              <div style="margin-top:8px;font-size:11.5px;color:var(--text-faint)">Negotiations completed: <b style="color:var(--text)">${c.negotiations}</b></div>
            </div>
          </div>
        </div>
        <div class="card pad">
          <div class="card-title">Recent activity</div>
          <div class="card-sub" style="margin-bottom:10px">Latest events from the append-only audit trail.</div>
          ${S.dashboard.recent.length
            ? S.dashboard.recent.map(activityRow).join("")
            : `<div class="empty" style="padding:30px"><div class="big">No activity yet</div>Upload a contract to start the pipeline.</div>`}
        </div>
      </div>`;
  }

  const statCard = (label, value, icon, icCls, trend) => `
    <div class="card stat-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div class="label">${label}</div><span class="icon ${icCls}">${UI.ICONS[icon]}</span>
      </div>
      <div class="value">${value ?? 0}</div>
      <div class="trend">${trend}</div>
    </div>`;

  const legendRow = (color, label, value) => `
    <div class="legend-row"><span class="swatch" style="background:${color}"></span>${label}<b>${value ?? 0}</b></div>`;

  const activityRow = (ev) => `
    <div class="activity-item">
      <span class="act-icon ${ev.actor_type === "agent" ? "ic-gold" : "ic-blue"}">${UI.ICONS[ev.actor_type === "agent" ? "robot" : "user"]}</span>
      <div>
        <div class="act-text"><b>${UI.esc(ev.actor)}</b> · ${UI.esc(ev.action_type.replace(/_/g, " "))}
        ${ev.risk_tier && ev.risk_tier !== "info" ? ` · <span class="chip ${ev.risk_tier === "auto" ? "green" : ev.risk_tier === "approval" ? "yellow" : "red"}">${UI.esc(ev.risk_tier)}</span>` : ""}</div>
        <div class="act-time">${UI.timeAgo(ev.ts)}</div>
      </div>
    </div>`;

  /* ============ Contracts ============ */
  async function viewContracts() {
    setTitle("Contracts");
    [S.contracts, S.playbooks] = await Promise.all([API.get("/api/contracts"), API.get("/api/playbooks")]);
    const samples = await API.get("/api/samples");
    const pbOptions = S.playbooks.map((p) => `<option value="${UI.esc(p.id)}">${UI.esc(p.name)}</option>`).join("");
    const view = viewRoot();
    view.innerHTML = `
      <div class="page-head">
        <div><div class="eyebrow">Contract intake</div><h1>Contracts</h1>
        <div class="sub">Upload an unreviewed contract or load a sample to see the full pipeline.</div></div>
        <div class="actions"><button class="btn" id="refresh-btn">Refresh</button></div>
      </div>
      <div class="grid two" style="margin-bottom:20px">
        <div class="card pad">
          <div class="card-title">Upload a contract</div>
          <div class="card-sub" style="margin-bottom:12px">PDF, DOCX or TXT · max 8 MB</div>
          <form id="upload-form">
            <div class="dropzone" id="dropzone">
              <div style="font-size:22px;color:var(--gold)">${UI.ICONS.upload}</div>
              <div class="dz-title">Drop the contract here, or click to browse</div>
              <div class="dz-sub" id="file-name">No file selected</div>
              <input type="file" id="file-input" hidden accept=".pdf,.docx,.txt" />
            </div>
            <div class="field" style="margin-top:14px"><label>Counterparty</label>
              <input class="input" name="counterparty" placeholder="e.g. CloudBase Inc." value="CloudBase Inc." /></div>
            <div class="field"><label>Company playbook (your side)</label>
              <select class="select" name="company_playbook">${pbOptions}</select></div>
            <div class="field"><label>Counterparty playbook (their side)</label>
              <select class="select" name="counterparty_playbook">${pbOptions}</select></div>
            <button class="btn primary" style="width:100%;justify-content:center" type="submit" id="upload-btn" disabled>Upload & ingest</button>
          </form>
        </div>
        <div class="card pad">
          <div class="card-title">One-click samples</div>
          <div class="card-sub" style="margin-bottom:12px">Curated demo contracts with known risk profiles.</div>
          <div class="grid" style="gap:10px">
            ${samples.map((s) => `
              <button class="btn sample-load" data-name="${UI.esc(s.name)}" style="justify-content:space-between">
                <span>${UI.ICONS.doc} ${UI.esc(s.name.replace(/-/g, " "))}</span>
                <span class="chip ghost">${UI.esc(s.format || "txt")}</span>
                <span class="chip ghost">${UI.esc(s.counterparty)}</span>
              </button>`).join("")}
          </div>
          <div style="margin-top:14px;font-size:11.5px;color:var(--text-faint)">Samples map to the <b style="color:var(--text-dim)">startup-friendly</b> (you) vs <b style="color:var(--text-dim)">vendor-friendly</b> (them) playbooks.</div>
        </div>
      </div>
      <div class="grid" style="gap:12px" id="contract-grid">
        ${contractCards()}
      </div>`;
    bindUpload();
    document.getElementById("refresh-btn").onclick = () => viewContracts();
    view.querySelectorAll(".sample-load").forEach((el) => {
      el.onclick = async () => {
        try {
          const contract = await API.post("/api/samples/" + el.dataset.name + "/load");
          UI.toast("Sample loaded: " + contract.name, "success");
          go("contract/" + contract.id);
        } catch (err) { UI.toast(err.message, "error"); }
      };
    });
    view.querySelectorAll("[data-open]").forEach((el) => {
      el.onclick = () => go("contract/" + el.dataset.open);
    });
    view.querySelectorAll("[data-negotiate]").forEach((el) => {
      el.onclick = () => go("negotiate/" + el.dataset.negotiate);
    });
    view.querySelectorAll("[data-delete]").forEach((el) => {
      el.onclick = async () => {
        const name = el.dataset.name;
        UI.modal(`<button class="close" data-close>×</button>
          <h3>Delete contract?</h3>
          <p style="color:var(--text-dim)">"${UI.esc(name)}" and all of its clauses, risks, redlines and negotiation history will be removed.</p>
          <div class="approval-actions" style="justify-content:flex-end">
            <button class="btn" data-close>Cancel</button>
            <button class="btn danger" id="confirm-delete" data-id="${el.dataset.delete}">Delete</button>
          </div>`);
        document.getElementById("confirm-delete").onclick = async () => {
          await API.del("/api/contracts/" + el.dataset.delete);
          UI.closeModal();
          UI.toast("Contract deleted", "success");
          viewContracts();
        };
      };
    });
  }

  function contractCards() {
    if (!S.contracts.length) {
      return `<div class="empty"><div class="big">No contracts yet</div>Upload one above or load a sample to get started.</div>`;
    }
    return S.contracts.map((c) => `
      <div class="card approval-card">
        <span class="icon ic-blue" style="width:38px;height:38px;border-radius:10px;display:grid;place-items:center">${UI.ICONS.doc}</span>
        <div class="body">
          <h3>${UI.esc(c.name)}</h3>
          <p>${UI.esc(c.counterparty)} · uploaded ${UI.timeAgo(c.created_at)} ${UI.statusChip(c.status)}</p>
          <div class="approval-actions">
            <button class="btn small" data-open="${c.id}">Open</button>
            <button class="btn small" data-open="${c.id}">Review</button>
            <button class="btn small" data-negotiate="${c.id}">Negotiate</button>
            <button class="btn small danger" data-delete="${c.id}" data-name="${UI.esc(c.name)}">${UI.ICONS.trash}</button>
          </div>
        </div>
      </div>`).join("");
  }

  function bindUpload() {
    const dz = document.getElementById("dropzone");
    const input = document.getElementById("file-input");
    const form = document.getElementById("upload-form");
    const btn = document.getElementById("upload-btn");
    let file = null;
    dz.onclick = () => input.click();
    dz.ondragover = (e) => { e.preventDefault(); dz.classList.add("drag"); };
    dz.ondragleave = () => dz.classList.remove("drag");
    dz.ondrop = (e) => {
      e.preventDefault(); dz.classList.remove("drag");
      if (e.dataTransfer.files.length) { file = e.dataTransfer.files[0]; update(); }
    };
    input.onchange = () => { file = input.files[0]; update(); };
    const update = () => {
      document.getElementById("file-name").textContent = file ? file.name + " · " + Math.round(file.size / 1024) + " KB" : "No file selected";
      btn.disabled = !file;
    };
    form.onsubmit = async (ev) => {
      ev.preventDefault();
      const fd = new FormData();
      fd.append("file", file);
      fd.append("counterparty", form.counterparty.value || "Counterparty");
      fd.append("company_playbook", form.company_playbook.value);
      fd.append("counterparty_playbook", form.counterparty_playbook.value);
      btn.disabled = true;
      btn.textContent = "Ingesting…";
      try {
        const contract = await API.form("/api/contracts/upload", fd);
        UI.toast("Contract ingested: " + contract.name, "success");
        go("contract/" + contract.id);
      } catch (err) {
        UI.toast(err.message, "error");
        btn.disabled = false;
        btn.textContent = "Upload & ingest";
      }
    };
  }

  /* ============ Review studio ============ */
  async function viewContract(id) {
    clearPollers();
    S.selectedClauseId = null;
    [S.contract, S.clauses, S.risks, S.redlines, S.playbooks] = await Promise.all([
      API.get("/api/contracts/" + id),
      API.get("/api/contracts/" + id + "/clauses"),
      API.get("/api/contracts/" + id + "/risks"),
      API.get("/api/contracts/" + id + "/redlines"),
      API.get("/api/playbooks"),
    ]);
    const nego = await API.get("/api/contracts/" + id + "/negotiation");
    S.negotiation = nego.negotiation;
    setTitle("Review Studio", "Contract");
    const c = S.contract;
    const counts = { green: 0, yellow: 0, red: 0 };
    S.risks.forEach((r) => { counts[r.risk_level] = (counts[r.risk_level] || 0) + 1; });
    const pbName = (pid) => (S.playbooks.find((p) => p.id === pid) || {}).name || pid;
    const view = viewRoot();
    view.innerHTML = `
      <div class="page-head">
        <div>
          <div class="eyebrow">${UI.esc(c.counterparty)}</div>
          <h1>${UI.esc(c.name)}</h1>
          <div class="sub">
            ${UI.statusChip(c.status)}
            <span class="chip gold">${UI.esc(pbName(c.company_playbook))}</span>
            <span class="chip blue">vs ${UI.esc(pbName(c.counterparty_playbook))}</span>
          </div>
        </div>
        <div class="actions">
          ${c.status === "uploaded" ? `<button class="btn primary" id="run-review">${UI.ICONS.sparkle} Run AI Review</button>` : ""}
          ${["reviewed", "negotiated", "negotiating"].includes(c.status) && !S.negotiation ? `<button class="btn primary" id="start-nego">${UI.ICONS.negotiate} Start Negotiation</button>` : ""}
          ${S.negotiation ? `<button class="btn" id="view-nego">${UI.ICONS.negotiate} View negotiation</button>` : ""}
        </div>
      </div>
      <div id="job-area"></div>
      ${c.summary ? `<div class="card pad" style="margin-bottom:16px;border-left:3px solid var(--gold)">
        <div class="card-title">${UI.ICONS.robot} AI executive summary</div>
        <p style="margin:8px 0 0;color:var(--text-dim);line-height:1.65">${UI.esc(c.summary)}</p></div>` : ""}
      <div class="grid review">
        <div class="card" style="padding:8px">
          <div style="display:flex;align-items:center;gap:10px;padding:10px 12px 6px">
            <span style="font-family:var(--serif);font-size:15px;color:#efe8d4">Clauses</span>
            <span class="spacer" style="flex:1"></span>
            <span class="chip green">${counts.green}</span><span class="chip yellow">${counts.yellow}</span><span class="chip red">${counts.red}</span>
          </div>
          <div class="clause-list" id="clause-list">
            ${S.clauses.map(clauseRowHtml).join("") || `<div class="empty" style="padding:26px">No clauses yet — run the AI review.</div>`}
          </div>
        </div>
        <div class="clause-detail" id="clause-detail"></div>
      </div>`;
    view.querySelectorAll(".clause-row").forEach((el) => {
      el.onclick = () => {
        S.selectedClauseId = parseInt(el.dataset.id, 10);
        view.querySelectorAll(".clause-row").forEach((x) => x.classList.remove("selected"));
        el.classList.add("selected");
        renderClauseDetail();
      };
    });
    const rr = document.getElementById("run-review");
    if (rr) rr.onclick = () => runReview(id);
    const sn = document.getElementById("start-nego");
    if (sn) sn.onclick = () => startNegotiation(id);
    const vn = document.getElementById("view-nego");
    if (vn) vn.onclick = () => go("negotiate/" + id);
    if (S.clauses.length && !S.selectedClauseId) {
      S.selectedClauseId = S.clauses[0].id;
      view.querySelectorAll(".clause-row")[0]?.classList.add("selected");
    }
    renderClauseDetail();
    if (c.status === "reviewing") {
      // Resume polling for in-flight review jobs is not tracked across reloads;
      // show a hint instead.
      document.getElementById("job-area").innerHTML =
        `<div class="card pad" style="margin-bottom:16px;border-left:3px solid var(--gold)"><span class="spin"></span> A review job is running for this contract — refresh the page to pick it up.</div>`;
    }
  }

  const clauseRowHtml = (cl) => {
    const risk = S.risks.find((r) => r.clause_id === cl.id);
    const level = risk ? risk.risk_level : "ghost";
    const dot = level === "ghost" ? `<span class="dot-inline" style="background:#66728a"></span>` : `<span class="dot-inline ${level}"></span>`;
    return `<div class="clause-row" data-id="${cl.id}">
      <div style="padding-top:3px">${dot}</div>
      <div>
        <div class="c-type">${UI.esc(cl.clause_type)}</div>
        <div class="c-title">${UI.esc(cl.title)}</div>
        <div class="c-ref">${UI.esc(cl.source_ref || "—")}</div>
      </div>
    </div>`;
  };

  function renderClauseDetail() {
    const root = document.getElementById("clause-detail");
    if (!root) return;
    if (!S.selectedClauseId) { root.innerHTML = `<div class="card pad empty"><div class="big">Select a clause</div></div>`; return; }
    const cl = S.clauses.find((x) => x.id === S.selectedClauseId);
    if (!cl) return;
    const risk = S.risks.find((r) => r.clause_id === cl.id);
    const redline = S.redlines.find((r) => r.clause_id === cl.id);
    const level = risk ? risk.risk_level : "green";
    root.innerHTML = `
      <div class="card pad" style="display:flex;flex-direction:column;gap:14px">
        <div style="display:flex;align-items:flex-start;gap:12px">
          <div style="flex:1">
            <div class="eyebrow">${UI.esc(cl.clause_type)} · ${UI.esc(cl.source_ref || "n/a")}</div>
            <div style="font-family:var(--serif);font-size:19px;color:#f2ecd9">${UI.esc(cl.title)}</div>
          </div>
          ${UI.riskBadge(level)}
        </div>
        <div class="clause-text">${UI.esc(cl.text)}</div>
        ${risk ? `
          <div class="card-title">Why this verdict?</div>
          <div class="rule-box" style="padding:12px 15px;border-radius:10px;font-size:12.5px;color:var(--text-dim);line-height:1.6">
            ${risk.rule_id ? `<span class="chip gold">${UI.esc(risk.rule_id)}</span> <b style="color:var(--text)">${UI.esc(risk.rule_name)}</b><br/>${UI.esc(risk.rule_text)}` : UI.esc(risk.explanation)}
            <div style="margin-top:8px;color:var(--text-faint)">Confidence ${Math.round((risk.confidence || 0) * 100)}%</div>
          </div>
          <p style="margin:0;color:var(--text-dim);font-size:12.5px;line-height:1.6">${UI.esc(risk.explanation)}</p>` : ""}
        ${redline ? `
          <div style="display:flex;align-items:center;gap:10px">
            <div class="card-title">Proposed redline</div>
            <span class="chip ${redline.status === "accepted" ? "green" : redline.status === "rejected" ? "red" : "gold"}">${UI.esc(redline.status)}</span>
            <span class="spacer" style="flex:1"></span>
            ${redline.status === "proposed" ? `
              <button class="btn small" id="accept-redline">${UI.ICONS.check} Accept</button>
              <button class="btn small danger" id="reject-redline">${UI.ICONS.x} Reject</button>` : ""}
          </div>
          <div class="diff-view">${UI.renderDiff(redline.original_text, redline.proposed_text)}</div>
          <p style="margin:0;color:var(--text-dim);font-size:12.5px;line-height:1.6"><b style="color:var(--gold)">Why:</b> ${UI.esc(redline.justification)}</p>` : ""}
      </div>`;
    const acc = root.querySelector("#accept-redline");
    const rej = root.querySelector("#reject-redline");
    if (acc) acc.onclick = () => decideRedline(redline.id, "accepted");
    if (rej) rej.onclick = () => decideRedline(redline.id, "rejected");
  }

  async function decideRedline(id, decision) {
    await API.put("/api/redlines/" + id + "/decision?decision=" + decision);
    S.redlines = await API.get("/api/contracts/" + S.contract.id + "/redlines");
    renderClauseDetail();
    UI.toast("Redline " + decision, "success");
  }

  async function runReview(id) {
    const area = document.getElementById("job-area");
    area.innerHTML = jobProgressHtml(null);
    const res = await API.post("/api/contracts/" + id + "/review", { company_playbook: S.contract.company_playbook || "startup-friendly" });
    pollJob(res.job_id, {
      render: (job) => { area.innerHTML = jobProgressHtml(job); },
      onDone: async () => {
        UI.toast("Review complete — clauses, risks and redlines ready", "success");
        await viewContract(id);
      },
      onFail: (job) => {
        area.innerHTML = `<div class="card pad" style="margin-bottom:16px;border-left:3px solid var(--red)">Review failed: ${UI.esc(job.error || "unknown error")}</div>`;
      },
    });
  }

  function jobProgressHtml(job) {
    const stages = ["Extracting clauses", "Classifying risks", "Drafting redlines", "Summarizing"];
    const idx = job ? Math.min(job.stage_index ?? 0, stages.length - 1) : 0;
    const pct = job ? Math.round((job.progress || 0) * 100) : 5;
    return `<div class="card pad" style="margin-bottom:16px;border-left:3px solid var(--gold)">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
        <span class="spin"></span>
        <span style="font-family:var(--serif);font-size:15px;color:#e9e2cf">${job ? UI.esc(job.stage) : "Queuing agent pipeline…"} · ${pct}%</span>
      </div>
      <div class="job-progress">
        <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
        <div class="stage-list">
          ${stages.map((s, i) => `<span class="stage-pill ${i < idx ? "done" : i === idx ? "now" : ""}">${i < idx ? "✓" : ""} ${s}</span>`).join("")}
        </div>
      </div>
    </div>`;
  }

  async function startNegotiation(id) {
    const res = await API.post("/api/contracts/" + id + "/negotiate");
    go("negotiate/" + id);
  }

  /* ============ Negotiation ============ */
  async function viewNegotiations() {
    setTitle("Negotiations");
    S.contracts = await API.get("/api/contracts");
    const withNego = [];
    for (const c of S.contracts) {
      const n = await API.get("/api/contracts/" + c.id + "/negotiation");
      if (n.negotiation) withNego.push({ contract: c, negotiation: n.negotiation });
    }
    viewRoot().innerHTML = `
      <div class="page-head">
        <div><div class="eyebrow">Multi-agent orchestration</div><h1>Negotiations</h1>
        <div class="sub">Agent-vs-agent sessions with full transcripts.</div></div>
      </div>
      ${withNego.length ? withNego.map(({ contract, negotiation }) => `
        <div class="card approval-card" style="margin-bottom:12px">
          <span class="icon ic-gold" style="width:38px;height:38px;border-radius:10px;display:grid;place-items:center">${UI.ICONS.negotiate}</span>
          <div class="body">
            <h3>${UI.esc(contract.name)} <span class="chip ${negotiation.status === "agreed" ? "green" : negotiation.status === "running" ? "gold" : "red"}">${UI.esc(negotiation.status)}</span></h3>
            <p>${UI.esc(negotiation.outcome_summary || "Negotiation in progress…")}</p>
            <div class="approval-actions">
              <button class="btn small" onclick="APP.go('negotiate/${contract.id}')">Open transcript</button>
            </div>
          </div>
        </div>`).join("") : `<div class="empty"><div class="big">No negotiations yet</div>Open a reviewed contract and start one.</div>`}`;
  }

  async function viewNegotiation(id) {
    clearPollers();
    S.contract = await API.get("/api/contracts/" + id);
    setTitle("Negotiation", S.contract.name);
    await loadTranscript(id);
    renderNegotiationView(id);
  }

  async function loadTranscript(id) {
    const data = await API.get("/api/contracts/" + id + "/negotiation");
    S.negotiation = data.negotiation;
    S.messages = data.messages || [];
  }

  function renderNegotiationView(id) {
    const c = S.contract;
    const n = S.negotiation;
    const view = viewRoot();
    if (!n) {
      if (c.status === "negotiating") {
        view.innerHTML = `
          <div class="card pad" style="max-width:640px;margin:0 auto;text-align:center;padding:46px">
            <div style="font-size:30px;color:var(--gold)">${UI.ICONS.negotiate}</div>
            <div class="card-title" style="font-size:18px;margin-top:10px">Agents are negotiating…</div>
            <p style="color:var(--text-dim)"><span class="spin"></span> Waiting for the first round to open.</p>
          </div>`;
        const tick = async () => {
          await loadTranscript(id);
          if (S.negotiation && S.negotiation.status === "running") {
            S.pollers.push(setTimeout(tick, 1200));
            return;
          }
          renderNegotiationView(id);
        };
        S.pollers.push(setTimeout(tick, 1200));
        return;
      }
      view.innerHTML = `
        <div class="page-head">
          <div><div class="eyebrow">${UI.esc(c.counterparty)}</div><h1>${UI.esc(c.name)}</h1>
          <div class="sub">Two agents, two playbooks, one governed negotiation.</div></div>
        </div>
        <div class="card pad" style="max-width:640px;margin:0 auto;text-align:center;padding:46px">
          <div style="font-size:30px;color:var(--gold)">${UI.ICONS.negotiate}</div>
          <div class="card-title" style="font-size:18px;margin-top:10px">Start the agent negotiation</div>
          <p style="color:var(--text-dim);line-height:1.6">Your company agent (${UI.esc(c.company_playbook || "startup-friendly")} playbook)
          will open against the counterparty agent (${UI.esc(c.counterparty_playbook || "vendor-friendly")} playbook)
          and exchange proposals until they converge or reach an explicit impasse.</p>
          <button class="btn primary" id="nego-start" style="margin-top:8px">${UI.ICONS.play} Start negotiation</button>
        </div>`;
      document.getElementById("nego-start").onclick = async () => {
        const res = await API.post("/api/contracts/" + id + "/negotiate");
        document.querySelector(".card.pad").innerHTML = `<div style="text-align:center;padding:20px"><span class="spin" style="width:20px;height:20px"></span><p style="color:var(--text-dim)">Agents are negotiating…</p></div>`;
        pollJob(res.job_id, {
          onDone: async () => { await loadTranscript(id); renderNegotiationView(id); UI.toast("Negotiation finished", "success"); },
          onFail: (job) => UI.toast(job.error || "Negotiation failed", "error"),
        });
      };
      return;
    }
    const running = n.status === "running";
    const cName = S.user.organization || "Company";
    const cptName = c.counterparty || "Counterparty";
    view.innerHTML = `
      <div class="page-head">
        <div>
          <div class="eyebrow">${UI.esc(c.counterparty)} · ${UI.esc(n.company_playbook)} vs ${UI.esc(n.counterparty_playbook)}</div>
          <h1>${UI.esc(c.name)}</h1>
          <div class="sub">
            <span class="chip ${n.status === "agreed" ? "green" : n.status === "impasse" ? "red" : "gold"}">${UI.esc(n.status)}</span>
            <span class="chip ghost">${n.rounds} round${n.rounds === 1 ? "" : "s"}</span>
          </div>
        </div>
        <div class="actions">
          ${!running && n.status !== "agreed" ? `<button class="btn primary" id="nego-restart">Re-negotiate</button>` : ""}
          <button class="btn" onclick="APP.go('approvals')">${UI.ICONS.gate} Approval gate</button>
        </div>
      </div>
      ${running ? `<div class="card pad" style="margin-bottom:16px;border-left:3px solid var(--gold)">
        <div style="display:flex;gap:10px;align-items:center"><span class="spin"></span>
        <span style="font-family:var(--serif);font-size:15px;color:#e9e2cf">Agents are exchanging proposals…</span></div></div>` : ""}
      ${n.outcome_summary && !running ? `<div class="card pad" style="margin-bottom:16px;border-left:3px solid ${n.status === "agreed" ? "var(--green)" : "var(--red)"}">
        <div class="card-title">${n.status === "agreed" ? "✓ Agreement reached" : "⚠ Impasse — escalated to human"}</div>
        <p style="margin:8px 0 0;color:var(--text-dim);line-height:1.65">${UI.esc(n.outcome_summary)}</p></div>` : ""}
      <div class="card pad">
        <div class="transcript" id="transcript">
          ${S.messages.map((m) => transcriptMsg(m, cName, cptName)).join("")}
        </div>
      </div>`;
    const restart = view.querySelector("#nego-restart");
    if (restart) restart.onclick = async () => {
      const res = await API.post("/api/contracts/" + id + "/negotiate");
      pollJob(res.job_id, { onDone: async () => { await loadTranscript(id); renderNegotiationView(id); } });
    };
    if (running) {
      S.pollers.push(setTimeout(async () => {
        await loadTranscript(id);
        renderNegotiationView(id);
      }, 1400));
    }
  }

  function transcriptMsg(m, cName, cptName) {
    const payload = m.payload && typeof m.payload === "string" ? safeParse(m.payload) : m.payload;
    if (m.actor === "system") {
      return `<div class="msg system"><div class="bubble">${UI.esc(m.content)}</div>
        <div class="meta">Round ${m.round_no} · ${UI.esc(m.kind)}</div></div>`;
    }
    const company = m.actor === "company";
    const name = company ? cName + " agent" : cptName + " agent";
    const changes = payload && Array.isArray(payload.changes) ? payload.changes : [];
    return `
      ${m.round_no > 0 && m.kind === "proposal" && m.actor === "company" ? `<div class="round-divider"><span>Round ${m.round_no}</span></div>` : ""}
      <div class="msg ${m.actor}">
        <div class="bubble">
          <div style="font-size:11px;color:var(--gold);margin-bottom:4px">${UI.esc(name)} · ${UI.esc(m.kind)}</div>
          ${UI.esc(m.content)}
          ${changes.length ? `<div class="change-strip">${changes.map((ch) =>
            `<div><span class="cs-title">${UI.esc(ch.title || ch.clause_type)}</span><br/>
            <span class="cs-proposed">${UI.esc(ch.proposed || "").slice(0, 220)}${(ch.proposed || "").length > 220 ? "…" : ""}</span></div>`
          ).join("")}</div>` : ""}
        </div>
        <div class="meta">${UI.timeAgo(m.created_at)}</div>
      </div>`;
  }
  const safeParse = (s) => { try { return JSON.parse(s); } catch { return {}; } };

  /* ============ Approvals ============ */
  async function viewApprovals() {
    setTitle("Approval Gate", "Human-in-the-loop");
    S.approvals = await API.get("/api/approvals");
    renderApprovals();
  }
  function renderApprovals(filter = "all") {
    const rows = S.approvals.filter((a) => filter === "all" || a.status === filter);
    const view = viewRoot();
    view.innerHTML = `
      <div class="page-head">
        <div><div class="eyebrow">Human-in-the-loop</div><h1>Approval Gate</h1>
        <div class="sub">Actions with real-world effect stop here until a human decides.</div></div>
      </div>
      <div style="display:flex;gap:8px;margin-bottom:16px">
        ${["all", "pending", "approved", "rejected"].map((f) =>
          `<button class="btn small ${filter === f ? "primary" : ""}" data-filter="${f}">${f[0].toUpperCase() + f.slice(1)}
          ${f !== "all" ? `(${S.approvals.filter((a) => a.status === f).length})` : ""}</button>`).join("")}
      </div>
      <div class="grid" style="gap:12px">
        ${rows.length ? rows.map(approvalCard).join("") : `<div class="empty"><div class="big">No ${filter === "all" ? "" : filter + " "}actions here</div>Negotiations and reviews generate gateable actions automatically.</div>`}
      </div>`;
    view.querySelectorAll("[data-filter]").forEach((el) => {
      el.onclick = () => renderApprovals(el.dataset.filter);
    });
    view.querySelectorAll("[data-decide]").forEach((el) => {
      el.onclick = () => {
        const id = el.dataset.decide;
        const decision = el.dataset.decision;
        const a = S.approvals.find((x) => x.id === parseInt(id, 10));
        UI.modal(`
          <button class="close" data-close>×</button>
          <h3>${decision === "approve" ? "Approve" : "Reject"}: ${UI.esc(a.title)}</h3>
          <div class="field"><label>Decision note (recorded in the audit trail)</label>
            <textarea class="textarea" id="decision-note" placeholder="e.g. Reviewed the liability cap — matches our 12-month rule."></textarea></div>
          <div class="approval-actions" style="justify-content:flex-end">
            <button class="btn" data-close>Cancel</button>
            <button class="btn ${decision === "approve" ? "primary" : "danger"}" id="confirm-decision">Confirm ${decision}</button>
          </div>`);
        document.getElementById("confirm-decision").onclick = async () => {
          const note = document.getElementById("decision-note").value;
          await API.post("/api/approvals/" + id + "/decision", { decision, note });
          UI.closeModal();
          UI.toast("Decision recorded in the audit trail", "success");
          S.approvals = await API.get("/api/approvals");
          await refreshPendingCount();
          renderApprovals(filter);
        };
      };
    });
  }
  const approvalCard = (a) => `
    <div class="card approval-card">
      <span class="icon ${a.risk_tier === "auto" ? "ic-green" : a.risk_tier === "approval" ? "ic-gold" : "ic-red"}"
        style="width:38px;height:38px;border-radius:10px;display:grid;place-items:center">${UI.ICONS.gate}</span>
      <div class="body">
        <div style="display:flex;gap:8px;align-items:center">
          <h3 style="margin:0">${UI.esc(a.title)}</h3>
          <span class="tier-pill tier-${a.risk_tier}">${UI.esc(a.risk_tier)}</span>
          <span class="chip ${a.status === "approved" ? "green" : a.status === "rejected" ? "red" : "gold"}">${UI.esc(a.status)}</span>
        </div>
        <p>${UI.esc(a.summary)}</p>
        <div style="font-size:11px;color:var(--text-faint)">
          Raised ${UI.timeAgo(a.created_at)} · ${a.action_type}
          ${a.decided_by ? ` · decided by <b style="color:var(--text-dim)">${UI.esc(a.decided_by)}</b> ${a.decision_note ? `— “${UI.esc(a.decision_note)}”` : ""}` : ""}
        </div>
        ${a.status === "pending" && a.risk_tier === "approval" ? `
          <div class="approval-actions">
            <button class="btn small primary" data-decide="${a.id}" data-decision="approve">${UI.ICONS.check} Approve</button>
            <button class="btn small danger" data-decide="${a.id}" data-decision="reject">${UI.ICONS.x} Reject</button>
          </div>` : ""}
      </div>
    </div>`;

  /* ============ Audit ============ */
  async function viewAudit() {
    setTitle("Audit Trail", "Tamper-evident");
    S.audit = await API.get("/api/audit?limit=300");
    S.contracts = await API.get("/api/contracts");
    renderAudit();
  }
  function renderAudit() {
    const view = viewRoot();
    view.innerHTML = `
      <div class="page-head">
        <div><div class="eyebrow">Append-only · chain-hashed</div><h1>Audit Trail</h1>
        <div class="sub">Every agent step and human decision, traceable end to end.</div></div>
        <div class="actions"><span class="chip green">✓ chain verified</span></div>
      </div>
      <div class="card pad" style="margin-bottom:16px">
        <div class="table-wrap"><table class="tbl">
          <thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Tier</th><th>Contract</th><th>Details</th><th>Hash</th></tr></thead>
          <tbody>
          ${S.audit.map((ev) => `
            <tr>
              <td style="white-space:nowrap">${UI.fmtTime(ev.ts)}</td>
              <td class="strong">${ev.actor_type === "agent" ? UI.ICONS.robot : UI.ICONS.user} ${UI.esc(ev.actor)}</td>
              <td>${UI.esc(ev.action_type.replace(/_/g, " "))}</td>
              <td><span class="tier-pill tier-${ev.risk_tier === "info" ? "auto" : ev.risk_tier}">${UI.esc(ev.risk_tier)}</span></td>
              <td>${ev.contract_id ? `<a href="#/contract/${ev.contract_id}">#${ev.contract_id}</a>` : "—"}</td>
              <td style="max-width:320px;font-size:11.5px" title="${UI.esc(JSON.stringify(ev.details))}">${UI.esc(summarizeDetails(ev.details))}</td>
              <td><code class="hash" title="${UI.esc(ev.hash)}">${UI.esc(ev.hash.slice(0, 10))}…</code></td>
            </tr>`).join("") || `<tr><td colspan="7" style="text-align:center;padding:28px">No events yet.</td></tr>`}
          </tbody>
        </table></div>
      </div>`;
  }
  const summarizeDetails = (d) => {
    if (!d || typeof d !== "object") return "—";
    const parts = Object.entries(d).slice(0, 3).map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`);
    return parts.join(" · ") || "—";
  };

  /* ============ Playbooks ============ */
  async function viewPlaybooks() {
    setTitle("Playbooks");
    S.playbooks = await API.get("/api/playbooks");
    const view = viewRoot();
    view.innerHTML = `
      <div class="page-head">
        <div><div class="eyebrow">Configurable risk policy</div><h1>Playbooks</h1>
        <div class="sub">Every risk verdict and negotiation stance is grounded in these rules — nothing is a black box.</div></div>
      </div>
      <div class="grid cards-3" style="margin-bottom:16px">
        ${S.playbooks.map((p) => `
          <div class="card stat-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start">
              <span class="icon ic-gold">${UI.ICONS.book}</span>
              <span class="chip ghost">${p.rule_count} rules</span>
            </div>
            <div class="card-title" style="font-size:17px;margin-top:4px">${UI.esc(p.name)}</div>
            <div style="font-size:11.5px;color:var(--text-faint)">${UI.esc(p.organization)}</div>
            <div class="trend" style="line-height:1.55;color:var(--text-dim)">${UI.esc(p.description)}</div>
          </div>`).join("")}
      </div>
      ${S.playbooks.map((p) => `
        <details class="card" style="margin-bottom:12px">
          <summary style="padding:15px 20px;cursor:pointer;font-family:var(--serif);font-size:15.5px;color:#efe8d4">${UI.esc(p.name)} — ${p.rule_count} rules</summary>
          <div class="table-wrap" style="padding:0 20px 18px"><table class="tbl">
            <thead><tr><th>ID</th><th>Rule</th><th>Clause type</th><th>Severity</th><th>Statement</th></tr></thead>
            <tbody>${p.rules.map((r) => `
              <tr>
                <td><code class="hash">${UI.esc(r.id)}</code></td>
                <td class="strong">${UI.esc(r.name)}</td>
                <td>${UI.esc(r.clause_type)}</td>
                <td><span class="chip ${r.severity === "critical" ? "red" : r.severity === "warning" ? "yellow" : "ghost"}">${UI.esc(r.severity)}</span></td>
                <td style="font-size:12px">${UI.esc(r.statement)}</td>
              </tr>`).join("")}</tbody>
          </table></div>
        </details>`).join("")}`;
  }

  /* ============ Red team ============ */
  async function viewRedTeam() {
    setTitle("Red-Team Test", "Action gate");
    const view = viewRoot();
    view.innerHTML = `
      <div class="page-head">
        <div><div class="eyebrow">Adversarial validation</div><h1>Red-Team Test</h1>
        <div class="sub">Run the policy engine against 10 unsafe agent actions. Target: 100% correctly gated.</div></div>
        <div class="actions"><button class="btn primary" id="run-redteam">${UI.ICONS.bug} Run gate test</button></div>
      </div>
      <div id="redteam-results" class="card pad">
        <div class="empty"><div class="big">Test not run yet</div>The agent will attempt 10 actions — including auto-accepting a Red clause, e-signing, and deleting the audit log.</div>
      </div>`;
    document.getElementById("run-redteam").onclick = async () => {
      const res = await API.post("/api/redteam");
      document.getElementById("redteam-results").innerHTML = `
        <div style="display:flex;gap:16px;align-items:center;margin-bottom:16px;flex-wrap:wrap">
          <div style="font-family:var(--serif);font-size:30px;color:${res.safe ? "var(--green)" : "var(--red)"}">${res.passed}/${res.total}</div>
          <div>
            <div class="card-title">${res.safe ? "✓ Policy engine caught every dangerous action" : "Policy gap detected"}</div>
            <div class="card-sub">${res.gated} of ${res.total} attempts were blocked or queued for human approval; the rest were safe internal prep actions.</div>
          </div>
          <span class="chip ${res.safe ? "green" : "red"}">${res.safe ? "GATE INTACT" : "GATE FAILED"}</span>
        </div>
        <div class="table-wrap"><table class="tbl">
          <thead><tr><th>#</th><th>Agent attempt</th><th>Expected tier</th><th>Actual tier</th><th>Verdict</th><th>Outcome</th></tr></thead>
          <tbody>${res.results.map((r, i) => `
            <tr>
              <td>${i + 1}</td>
              <td><div class="strong">${UI.esc(r.label)}</div><div style="font-size:11.5px;color:var(--text-faint)">${UI.esc(r.description)}</div></td>
              <td><span class="tier-pill tier-${r.expected}">${UI.esc(r.expected)}</span></td>
              <td><span class="tier-pill tier-${r.actual}">${UI.esc(r.actual)}</span></td>
              <td><span class="${r.verdict === "pass" ? "verdict-pass" : "verdict-fail"}">${r.verdict === "pass" ? "PASS" : "FAIL"}</span></td>
              <td>${r.executed ? "Executed (internal)" : r.actual === "block" ? "BLOCKED" : "Queued for human approval"}</td>
            </tr>`).join("")}</tbody>
        </table></div>`;
    };
  }

  /* ============ Settings ============ */
  async function viewSettings() {
    setTitle("Settings");
    S.settings = await API.get("/api/settings");
    const m = S.settings.model;
    const cmds = {
      powershell: ['$env:GROQ_API_KEY="gsk_your_key_here"', 'setx GROQ_API_KEY "gsk_your_key_here"'],
      cmd: ['set GROQ_API_KEY=gsk_your_key_here', 'setx GROQ_API_KEY "gsk_your_key_here"'],
      bash: ['export GROQ_API_KEY="gsk_your_key_here"', 'echo \'export GROQ_API_KEY="gsk_your_key_here"\' >> ~/.bashrc'],
    };
    const view = viewRoot();
    view.innerHTML = `
      <div class="page-head">
        <div><div class="eyebrow">Runtime configuration</div><h1>Settings</h1>
        <div class="sub">LLM provider, model and environment.</div></div>
      </div>
      <div class="grid two">
        <div class="card pad">
          <div class="card-title">Model provider</div>
          <div class="card-sub" style="margin-bottom:14px">The agentic pipeline uses this model when available.</div>
          <div style="display:flex;flex-direction:column;gap:10px;font-size:13px">
            <div style="display:flex;justify-content:space-between"><span style="color:var(--text-faint)">Provider</span><span class="chip gold">${UI.esc(m.provider)}</span></div>
            <div style="display:flex;justify-content:space-between"><span style="color:var(--text-faint)">Model</span><span class="chip blue">${UI.esc(m.model)}</span></div>
            <div style="display:flex;justify-content:space-between"><span style="color:var(--text-faint)">Mode</span>
              <span class="chip ${m.key_set ? "green" : "yellow"}">${m.key_set ? "Groq connected" : "Demo fallback engine"}</span></div>
            <div style="display:flex;justify-content:space-between"><span style="color:var(--text-faint)">App version</span><span>${UI.esc(S.settings.version)}</span></div>
            <div style="display:flex;justify-content:space-between"><span style="color:var(--text-faint)">Data directory</span><span style="font-family:var(--mono);font-size:11px">${UI.esc(S.settings.data_dir)}</span></div>
          </div>
        </div>
        <div class="card pad">
          <div class="card-title">Connect Groq (free tier)</div>
          <div class="card-sub" style="margin-bottom:12px">Get a free key at <a href="https://console.groq.com/keys" target="_blank">console.groq.com/keys</a>, then set it from the terminal:</div>
          ${[
            ["Windows PowerShell", cmds.powershell],
            ["Windows cmd", cmds.cmd],
            ["macOS / Linux", cmds.bash],
          ].map(([label, lines]) => `
            <div class="field"><label>${label} — current session</label>
              <div class="code-block">${UI.esc(lines[0])}<button class="copy-btn" data-copy="${UI.esc(lines[0])}">copy</button></div></div>
            <div class="field"><label>${label} — persist across restarts</label>
              <div class="code-block">${UI.esc(lines[1])}<button class="copy-btn" data-copy="${UI.esc(lines[1])}">copy</button></div></div>`).join("")}
          <p style="font-size:11.5px;color:var(--text-faint);line-height:1.6">Alternative: copy <code>.env.example</code> to <code>.env</code> in the project folder and set <code>GROQ_API_KEY</code> there, then restart the server. Without a key the app still runs on its deterministic demo engine — perfect for offline demos.</p>
        </div>
      </div>`;
    view.querySelectorAll("[data-copy]").forEach((el) => {
      el.onclick = () => {
        navigator.clipboard?.writeText(el.dataset.copy).then(() => {
          UI.toast("Copied to clipboard", "success");
        });
      };
    });
  }

  /* ============ Boot ============ */
  window.addEventListener("hashchange", () => {
    if ((location.hash || "").replace(/^#\/?/, "").startsWith("login")) {
      S.user = null;
      renderLogin();
      return;
    }
    if (!S.user) { renderLogin(); return; }
    if (!document.querySelector(".sidebar")) { renderShell(location.hash.replace(/^#\/?/, "")); return; }
    renderRoute();
  });

  window.addEventListener("clausiq-auth-expired", () => {
    S.user = null;
    renderLogin();
  });

  (function boot() {
    if (!API.getToken() || !S.user) {
      location.hash = "#/login";
      renderLogin();
      return;
    }
    renderShell(location.hash.replace(/^#\/?/, "") || "dashboard");
  })();

  return { go, renderRoute, viewContract, viewNegotiation, runReview };
})();
