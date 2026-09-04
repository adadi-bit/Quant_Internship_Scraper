/* Quant Radar front-end: all filtering/sorting happens in the browser. */
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];

  const FACETS = [
    { key: "hubs",        label: "Location",     multi: true },
    { key: "level",       label: "Level" },
    { key: "category",    label: "Role" },
    { key: "eligibility", label: "Student eligibility" },
    { key: "work_mode",   label: "Work mode" },
    { key: "season",      label: "Season" },
    { key: "source_type", label: "Source" },
    { key: "company",     label: "Company", searchable: true },
  ];
  const PAGE = 40;

  const state = {
    jobs: [], tab: "intern", sort: "posted", q: "", limit: PAGE, group: true,
    filters: Object.fromEntries(FACETS.map(f => [f.key, new Set()])),
    open: new Set(), expanded: new Set(), collapsedFacets: new Set(["season", "source_type", "company"]),
    facetShowAll: new Set(),
  };

  // ------------------------------------------------------------ URL state
  function readUrl() {
    const p = new URLSearchParams(location.search);
    for (const f of FACETS) if (p.get(f.key)) state.filters[f.key] = new Set(p.get(f.key).split("|"));
    if (p.get("tab")) state.tab = p.get("tab");
    if (p.get("sort")) state.sort = p.get("sort");
    if (p.get("q")) state.q = p.get("q");
  }
  function writeUrl() {
    const p = new URLSearchParams();
    for (const f of FACETS) if (state.filters[f.key].size) p.set(f.key, [...state.filters[f.key]].join("|"));
    if (state.tab !== "intern") p.set("tab", state.tab);
    if (state.sort !== "posted") p.set("sort", state.sort);
    if (state.q) p.set("q", state.q);
    history.replaceState(null, "", p.toString() ? "?" + p : location.pathname);
  }

  // ------------------------------------------------------------ helpers
  const dayMs = 86400000;
  const today = () => new Date(new Date().toDateString());
  function ago(iso) {
    if (!iso) return null;
    const d = Math.floor((today() - new Date(iso.slice(0, 10) + "T00:00:00")) / dayMs);
    if (d <= 0) return "today"; if (d === 1) return "yesterday";
    if (d < 30) return `${d}d ago`; if (d < 365) return `${Math.floor(d / 30)}mo ago`;
    return `${Math.floor(d / 365)}y ago`;
  }
  const isNew = j => (Date.now() - new Date(j.first_seen)) < 2 * dayMs;
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const colors = ["#1f5eff", "#0f8a5f", "#b26a00", "#7a3ff2", "#c2352e", "#0e7c86", "#a1258f", "#4b5563"];
  const color = name => colors[[...name].reduce((a, c) => a + c.charCodeAt(0), 0) % colors.length];
  const initials = name => name.split(/[\s(]+/).filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join("");
  const vals = (j, key) => Array.isArray(j[key]) ? j[key] : [j[key] ?? "Not specified"];

  // ------------------------------------------------------------ filtering
  function tabPass(j) {
    const s = j.user_status;
    switch (state.tab) {
      case "saved": return s === "saved";
      case "applied": return s === "applied";
      case "hidden": return s === "hidden";
      case "intern": return s !== "hidden" && j.active && j.level === "Internship";
      case "newgrad": return s !== "hidden" && j.active && j.level === "New Grad";
      default: return s !== "hidden";
    }
  }
  function facetPass(j, skipKey) {
    for (const f of FACETS) {
      if (f.key === skipKey) continue;
      const sel = state.filters[f.key];
      if (sel.size && !vals(j, f.key).some(v => sel.has(v))) return false;
    }
    return true;
  }
  function queryPass(j) {
    if (!state.q) return true;
    const q = state.q.toLowerCase();
    return (j.company + " " + j.title + " " + j.location).toLowerCase().includes(q);
  }
  const base = () => state.jobs.filter(j => tabPass(j) && queryPass(j));

  function sortJobs(list) {
    const key = { posted: j => j.posted_at || j.first_seen.slice(0, 10), added: j => j.first_seen, company: j => j.company.toLowerCase() }[state.sort];
    const dir = state.sort === "company" ? 1 : -1;
    return list.sort((a, b) => (key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : 0) * dir || a.company.localeCompare(b.company) || a.title.localeCompare(b.title));
  }

  // ------------------------------------------------------------ render facets
  function renderFacets() {
    const root = $("#facets");
    root.innerHTML = "";
    let active = 0;
    for (const f of FACETS) {
      const pool = base().filter(j => facetPass(j, f.key));
      const counts = new Map();
      for (const j of pool) for (const v of vals(j, f.key)) counts.set(v, (counts.get(v) || 0) + 1);
      for (const v of state.filters[f.key]) if (!counts.has(v)) counts.set(v, 0);
      const opts = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
      const sel = state.filters[f.key];
      active += sel.size ? 1 : 0;
      const collapsed = state.collapsedFacets.has(f.key);
      const showAll = state.facetShowAll.has(f.key);
      const shown = showAll ? opts : opts.slice(0, 8);
      const el = document.createElement("div");
      el.className = "facet";
      el.innerHTML = `
        <button class="facet-head" data-toggle="${f.key}">
          <span>${f.label}${sel.size ? ` <span class="sel">· ${sel.size} selected</span>` : ""}</span>
          <span class="chev">${collapsed ? "▶" : "▼"}</span>
        </button>
        <div class="facet-body ${collapsed ? "collapsed" : ""}">
          ${f.searchable ? `<input class="facet-search" placeholder="Find ${f.label.toLowerCase()}…" data-key="${f.key}">` : ""}
          ${shown.map(([v, n]) => `<label class="opt"><input type="checkbox" data-key="${f.key}" value="${esc(v)}" ${sel.has(v) ? "checked" : ""}> <span>${esc(v)}</span><span class="n">${n}</span></label>`).join("")}
          ${opts.length > 8 ? `<button class="facet-more" data-more="${f.key}">${showAll ? "Show fewer" : `Show all ${opts.length}`}</button>` : ""}
        </div>`;
      root.appendChild(el);
    }
    $("#active-filter-count").textContent = active + (state.q ? 1 : 0);
  }

  // ------------------------------------------------------------ render list
  function renderList() {
    const list = sortJobs(base().filter(j => facetPass(j)));
    const total = list.length;
    $("#match-count").textContent = `${total} matching role${total === 1 ? "" : "s"}`;
    $("#page-title").textContent = { intern: "Quant Internships", newgrad: "Quant New Grad Roles", all: "All Quant Roles", saved: "Saved roles", applied: "Applied roles", hidden: "Hidden roles" }[state.tab];
    const slice = list.slice(0, state.limit);
    const root = $("#list");
    root.innerHTML = "";
    if (!total) { root.innerHTML = `<div class="empty">No roles match. Try clearing a filter${state.jobs.length ? "" : " — or click <b>Refresh listings</b> to scrape"}.</div>`; }

    // group consecutive rows by company (keeps sort order)
    const groups = [];
    for (const j of slice) {
      const g = state.group && groups.length && groups[groups.length - 1].company === j.company ? groups[groups.length - 1] : null;
      if (g) g.jobs.push(j); else groups.push({ company: j.company, jobs: [j] });
    }
    let rank = 0;
    for (const g of groups) {
      const el = document.createElement("div");
      el.className = "company";
      const expanded = state.expanded.has(g.company) || g.jobs.length <= 3;
      const shown = expanded ? g.jobs : g.jobs.slice(0, 3);
      el.innerHTML = `
        <div class="company-head">
          <div class="avatar" style="background:${color(g.company)}">${esc(initials(g.company))}</div>
          <div><div class="company-name">${esc(g.company)}</div>
          <div class="company-meta">${g.jobs.length} role${g.jobs.length === 1 ? "" : "s"} · ${esc([...new Set(g.jobs.flatMap(j => j.hubs))].slice(0, 4).join(", "))}</div></div>
        </div>
        ${shown.map(j => roleHtml(j, ++rank)).join("")}
        ${g.jobs.length > 3 ? `<button class="more-roles" data-company="${esc(g.company)}">${expanded ? "Hide" : `View ${g.jobs.length - 3} more roles ↓`}</button>` : ""}`;
      if (!expanded) rank += g.jobs.length - 3;
      root.appendChild(el);
    }
    $("#showing").textContent = total ? `${Math.min(state.limit, total)} of ${total} showing` : "";
    $("#load-more").classList.toggle("hidden", state.limit >= total);
    $("#load-more").textContent = `Load more (${Math.max(0, total - state.limit)} remaining)`;
  }

  function roleHtml(j, rank) {
    const posted = j.posted_at ? `Opened ${ago(j.posted_at)}` : `Added ${ago(j.first_seen)}`;
    const st = j.user_status;
    return `
      <div class="role ${st === "hidden" || !j.active ? "dim" : ""}" data-id="${j.id}">
        <div class="rank">#${rank}</div>
        <div>
          <div class="role-title">
            <a href="${esc(j.url)}" target="_blank" rel="noopener">${esc(j.title)}</a>
            <span class="tag level ${j.level === "New Grad" ? "ng" : "in"}">${esc(j.level)}${j.level === "Internship" && j.eligibility !== "Not specified" ? " · " + esc(j.eligibility) : ""}</span>
            <span class="tag cat">${esc(j.category)}</span>
            ${isNew(j) && j.active ? `<span class="tag new">New</span>` : ""}
            ${!j.active ? `<span class="tag closed">Closed</span>` : ""}
            ${st ? `<span class="tag status">${st}</span>` : ""}
          </div>
          <div class="role-meta">
            <span>📍 ${esc(j.location || j.hubs.join(", ") || "Not specified")}</span>
            <span>🏢 ${esc(j.work_mode)}</span>
            ${j.season !== "Not specified" ? `<span>🗓 ${esc(j.season)}</span>` : ""}
            <span>${posted}</span>
          </div>
          ${state.open.has(j.id) ? `<div class="details" style="margin-top:10px"><div class="src">Source: ${esc(j.source)} · first seen ${j.first_seen.slice(0, 10)} · last seen ${j.last_seen.slice(0, 10)}</div>${esc(j.description || "No description captured — open the posting.")}</div>` : ""}
        </div>
        <div class="actions">
          <button class="btn" data-act="details" data-id="${j.id}">${state.open.has(j.id) ? "Hide details" : "View details"}</button>
          <button class="btn ${st === "saved" ? "on" : ""}" data-act="saved" data-id="${j.id}">${st === "saved" ? "Saved ✓" : "Save"}</button>
          <button class="btn ${st === "applied" ? "on" : ""}" data-act="applied" data-id="${j.id}">${st === "applied" ? "Applied ✓" : "Mark applied"}</button>
          <button class="btn ${st === "hidden" ? "on" : ""}" data-act="hidden" data-id="${j.id}">${st === "hidden" ? "Unhide" : "Hide"}</button>
          <a class="btn apply" href="${esc(j.url)}" target="_blank" rel="noopener">Apply →</a>
        </div>
      </div>`;
  }

  function render() { renderFacets(); renderList(); renderCounts(); writeUrl(); }
  function renderCounts() {
    for (const s of ["saved", "applied", "hidden"]) $(`#cnt-${s}`).textContent = state.jobs.filter(j => j.user_status === s).length;
  }

  // ------------------------------------------------------------ events
  document.addEventListener("click", async e => {
    const t = e.target.closest("button, a");
    if (!t) return;
    if (t.dataset.tab) { state.tab = t.dataset.tab; state.limit = PAGE; $$("#tabs button").forEach(b => b.classList.toggle("active", b === t)); render(); }
    else if (t.dataset.sort) { state.sort = t.dataset.sort; $$(".sort button").forEach(b => b.classList.toggle("active", b === t)); renderList(); writeUrl(); }
    else if (t.dataset.toggle) { const k = t.dataset.toggle; state.collapsedFacets.has(k) ? state.collapsedFacets.delete(k) : state.collapsedFacets.add(k); renderFacets(); }
    else if (t.dataset.more) { const k = t.dataset.more; state.facetShowAll.has(k) ? state.facetShowAll.delete(k) : state.facetShowAll.add(k); renderFacets(); }
    else if (t.dataset.company) { const c = t.dataset.company; state.expanded.has(c) ? state.expanded.delete(c) : state.expanded.add(c); renderList(); }
    else if (t.id === "load-more") { state.limit += PAGE; renderList(); }
    else if (t.id === "reset-filters") { for (const f of FACETS) state.filters[f.key].clear(); state.q = ""; $("#q").value = ""; state.limit = PAGE; render(); }
    else if (t.id === "share-btn") { e.preventDefault(); navigator.clipboard?.writeText(location.href); t.textContent = "Link copied ✓"; setTimeout(() => t.textContent = "Share view", 1500); }
    else if (t.dataset.act === "details") { const id = t.dataset.id; state.open.has(id) ? state.open.delete(id) : state.open.add(id); renderList(); }
    else if (t.dataset.act) {
      const j = state.jobs.find(x => x.id === t.dataset.id);
      const next = j.user_status === t.dataset.act ? null : t.dataset.act;
      j.user_status = next;
      saveStatus(j.id, next);
      render();
    }
  });
  document.addEventListener("change", e => {
    const t = e.target;
    if (t.matches(".facet-body input[type=checkbox]")) {
      const set = state.filters[t.dataset.key];
      t.checked ? set.add(t.value) : set.delete(t.value);
      state.limit = PAGE; render();
    } else if (t.id === "group-toggle") { state.group = t.checked; renderList(); }
  });
  document.addEventListener("input", e => {
    const t = e.target;
    if (t.id === "q") { state.q = t.value.trim(); state.limit = PAGE; render(); }
    else if (t.matches(".facet-search")) {
      const q = t.value.toLowerCase();
      $$(`.opt`, t.parentElement).forEach(o => o.classList.toggle("hidden", !o.textContent.toLowerCase().includes(q)));
    }
  });

  // ------------------------------------------------------------ data
  // Saved / Applied / Hidden live in this browser only (localStorage).
  const LS_KEY = "quantradar.status";
  function loadStatuses() { try { return JSON.parse(localStorage.getItem(LS_KEY) || "{}"); } catch { return {}; } }
  function saveStatus(id, status) {
    const all = loadStatuses();
    if (status) all[id] = status; else delete all[id];
    try { localStorage.setItem(LS_KEY, JSON.stringify(all)); } catch {}
  }
  function fmtWhen(iso) {
    const d = new Date(iso), h = Math.round((Date.now() - d) / 3600000);
    return h < 1 ? "just now" : h < 24 ? `${h}h ago` : ago(iso);
  }
  async function load() {
    const r = await fetch("jobs.json", { cache: "no-cache" }).then(r => r.json());
    const st = loadStatuses();
    state.jobs = r.jobs.map(j => ({ ...j, user_status: st[j.id] || null }));
    const lr = r.last_run;
    $("#last-run").textContent = lr ? `Updated ${fmtWhen(r.generated_at)} · ${lr.total_active} active · ${lr.new} new` : "No data yet";
    render();
  }

  readUrl();
  $("#q").value = state.q;
  $$("#tabs button").forEach(b => b.classList.toggle("active", b.dataset.tab === state.tab));
  $$(".sort button").forEach(b => b.classList.toggle("active", b.dataset.sort === state.sort));
  load();
})();
