"use strict";
/* NetArchitect dashboard - vanilla JS, no build step. */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n) => Number(n).toLocaleString();

const state = { presets: [], presetId: null, presetJson: {}, result: null, device: null,
                domain: "All", search: "" };

const MEDIUM_COLOR = { "Cat6a UTP": "var(--m-copper)", "OM4 MMF": "var(--m-mmf)",
                       "OS2 SMF": "var(--m-smf)", "Carrier circuit": "var(--m-carrier)" };
const SITE_COLORS = ["#0b6bcb", "#1a9b6c", "#c4581b", "#7b4fd1", "#b8324a", "#2b8fa3", "#8a7a12", "#5d6b7a"];

/* ------------------------------------------------------------------ API */
async function api(path, body) {
  const opts = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" },
                                           body: typeof body === "string" ? body : JSON.stringify(body) };
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({ message: `HTTP ${res.status}` }));
  if (!res.ok) { const err = new Error(data.message || `HTTP ${res.status}`); err.data = data; throw err; }
  return data;
}

function setStatus(text, kind = "idle") {
  const el = $("#status");
  el.textContent = text;
  el.className = `status ${kind}`;
}

function errorHtml(data) {
  if (!data) return "";
  const d = data.details || {};
  let html = `<h4>${esc(data.error || "Error")}${data.code ? ` · ${esc(data.code)}` : ""}</h4><div>${esc(data.message)}</div>`;
  if (d.issues && d.issues.length) html = `<h4>${esc(data.error)} · ${d.issues.length} issue(s)</h4><ul>${d.issues.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>`;
  if (d.attenuation_warning) html += `<div class="att"><b>Signal attenuation warning:</b> ${esc(d.attenuation_warning)}</div>`;
  if (d.minimum_prefix) html += `<div class="att">Minimum root prefix that would fit: <b>/${esc(d.minimum_prefix)}</b> (needs ${fmt(d.required)} addresses, ${fmt(d.available)} available)</div>`;
  return html;
}

function showError(data) {
  const box = $("#errorBox");
  if (!data) { box.hidden = true; box.innerHTML = ""; return; }
  box.innerHTML = errorHtml(data);
  box.hidden = false;
}

/* -------------------------------------------------------------- presets */
async function loadPresets() {
  state.presets = await api("/api/presets");
  const cards = state.presets.map((p) => `
    <button class="preset-card" data-id="${esc(p.id)}">
      <b>${esc(p.name)}</b><span>${esc(p.description)}</span>
    </button>`).join("") + `
    <button class="preset-card" data-id="custom"><b>Custom</b><span>Edit the JSON freely - every field is validated before the engines run.</span></button>`;
  $("#presetCards").innerHTML = cards;
  $$("#presetCards .preset-card").forEach((b) => b.addEventListener("click", () => selectPreset(b.dataset.id)));
  await selectPreset("campus_lan");
}

async function selectPreset(id) {
  $$("#presetCards .preset-card").forEach((b) => b.classList.toggle("active", b.dataset.id === id));
  state.presetId = id;
  if (id === "custom") {
    try {
      const cur = JSON.parse($("#paramEditor").value);
      cur.name = "Custom network"; cur.profile = "custom";
      $("#paramEditor").value = JSON.stringify(cur, null, 2);
    } catch { /* keep editor text as-is */ }
    return;
  }
  if (!state.presetJson[id]) state.presetJson[id] = await api(`/api/presets/${id}`);
  $("#paramEditor").value = JSON.stringify(state.presetJson[id], null, 2);
  await run();
}

/* ------------------------------------------------------------------ run */
async function run() {
  let params;
  try { params = JSON.parse($("#paramEditor").value); }
  catch (e) { showError({ error: "InvalidJSON", message: e.message }); setStatus("Invalid JSON", "bad"); return; }
  setStatus("Running…", "busy");
  $("#runBtn").disabled = true;
  try {
    state.result = await api("/api/plan", params);
    showError(null);
    const v = state.result.verification;
    setStatus(`${v.passed}/${v.total} checks passed`, v.passed === v.total ? "ok" : "bad");
    state.device = Object.keys(state.result.configs)[0];
    renderAll();
  } catch (e) {
    showError(e.data || { error: "Error", message: e.message });
    setStatus(e.data?.error || "Error", "bad");
  } finally { $("#runBtn").disabled = false; }
}

/* ------------------------------------------------------------- renderers */
function renderAll() {
  $("#empty").hidden = true;
  renderOverview(); renderTopology(); renderMedia(); renderAddressing();
  renderRouting(); renderConfigs(); renderRationale(); renderVerify();
  const active = $("#tabs button.active").dataset.tab;
  showTab(active);
}

function kpi(v, l) { return `<div class="kpi"><div class="v">${v}</div><div class="l">${esc(l)}</div></div>`; }

function renderOverview() {
  const r = state.result, a = r.addressing, m = r.meta;
  const hosts = a.blocks.reduce((s, b) => s + b.subnets.filter((x) => x.kind === "lan").reduce((t, x) => t + x.hosts_requested, 0), 0);
  const warns = r.rationale.filter((e) => e.level === "warning");
  const bgp = r.routing.bgp;
  $("#tab-overview").innerHTML = `
    <div class="kpis">
      ${kpi(Object.keys(r.topology.sites).length, "sites (on-prem)")}
      ${kpi(fmt(hosts), "hosts addressed")}
      ${kpi(a.subnet_count, "subnets allocated")}
      ${kpi(a.address_efficiency_pct + "%", "VLSM host efficiency")}
      ${kpi(a.root_utilization_pct + "%", `of ${esc(a.root)} used`)}
      ${kpi(r.topology.access_switches_total, "access switches sized")}
      ${kpi(Object.keys(r.configs).length, "device configs")}
      ${kpi(`${r.verification.passed}/${r.verification.total}`, "packet-flow checks")}
    </div>
    <div class="grid-2">
      <div class="card"><h3>${esc(m.name)}</h3>
        <dl class="facts">
          <dt>Network type</dt><dd>${esc(m.network_type)}</dd>
          <dt>Topology tier</dt><dd>${esc(r.topology.tier)}</dd>
          <dt>Routing</dt><dd>${esc(r.routing.design)}${bgp ? ` + eBGP AS${bgp.asn}` : ""}${r.routing.bfd ? " + BFD" : ""}</dd>
          <dt>Resiliency</dt><dd>${esc(m.resiliency)}</dd>
          <dt>Root prefix</dt><dd class="mono">${esc(m.root_prefix)}</dd>
          ${r.latency.worst ? `<dt>Worst latency</dt><dd>${r.latency.worst.one_way_ms} ms one-way (${esc(r.latency.worst.path.join(" → "))})${r.latency.budget_ms ? ` · budget ${r.latency.budget_ms} ms` : ""}</dd>` : ""}
        </dl>
      </div>
      <div class="card"><h3>Warnings &amp; advisories</h3>
        ${warns.length ? warns.map((w) => `<p class="small"><span class="pill warn">${esc(w.domain)}</span> <b>${esc(w.subject)}</b> — ${esc(w.justification)}</p>`).join("") : '<p class="muted">No warnings. Every link has optical headroom and every subnet fits.</p>'}
      </div>
    </div>
    <div class="card"><h3>Key decisions</h3>
      ${r.rationale.filter((e) => ["Topology", "L3 Routing"].includes(e.domain) && e.level !== "warning").slice(0, 4)
        .map((e) => `<p><span class="pill accent">${esc(e.domain)}</span> <b>${esc(e.decision)}</b><br><span class="muted small">${esc(e.justification)}</span></p>`).join("")}
    </div>`;
}

function renderTopology() {
  const r = state.result;
  const sites = r.addressing.blocks.filter((b) => b.site !== "INFRA").map((b) => b.site);
  const hub = r.routing.hub;
  const W = 760, H = 500, cx = W / 2, cy = H / 2;
  const pos = {};
  const ring = sites.filter((s) => !(r.meta.network_type !== "campus" && s === hub));
  if (r.meta.network_type !== "campus" && sites.includes(hub)) pos[hub] = [cx, cy];
  const R = Math.min(W, H) * 0.36;
  ring.forEach((s, i) => {
    const ang = -Math.PI / 2 + (2 * Math.PI * i) / ring.length;
    pos[s] = [cx + R * 1.45 * Math.cos(ang), cy + R * Math.sin(ang)];
  });
  const links = r.media.links;
  const hubLayout = r.meta.network_type !== "campus" && sites.includes(hub);
  const labelOf = (s) => {
    const blk = r.addressing.blocks.find((b) => b.site === s);
    const isCloud = !r.topology.sites[s];
    const area = r.routing.areas[s];
    const title = s + (s === hub && hubLayout ? " (hub)" : "") +
      (area !== undefined && r.routing.design.startsWith("Multi") ? ` · area ${area}` : "") +
      (isCloud ? " · AS" + (r.routing.bgp?.peers.find((p) => p.site === s)?.asn ?? "") : "");
    const sub = `${blk.block} · ${blk.subnets.length} subnets`;
    return { title, sub, isCloud, w: Math.max(title.length * 8.4, sub.length * 7) + 26 };
  };
  const halfW = Object.fromEntries(sites.map((s) => [s, labelOf(s).w / 2]));
  const edges = links.map((l) => {
    const [x1, y1] = pos[l.a], [x2, y2] = pos[l.b];
    let mx = (x1 + x2) / 2, my = (y1 + y2) / 2, path;
    if (hubLayout && l.a !== hub && l.b !== hub) {
      // bend spoke-to-spoke links away from the hub so they never cross it
      let dx = mx - cx, dy = my - cy, len = Math.hypot(dx, dy);
      if (len < 40) { dx = -(y2 - y1); dy = x2 - x1; len = Math.hypot(dx, dy); if (dx < 0) { dx = -dx; dy = -dy; } }
      const k = R * 0.75 / len, qx = mx + dx * k, qy = my + dy * k;
      path = `M${x1},${y1} Q${qx},${qy} ${x2},${y2}`;
      mx = 0.25 * x1 + 0.5 * qx + 0.25 * x2; my = 0.25 * y1 + 0.5 * qy + 0.25 * y2;
    } else {
      path = `M${x1},${y1} L${x2},${y2}`;
      // centre the label on the visible segment between the two node boxes
      const dx = Math.abs(x2 - x1) || 1e-6, dy = Math.abs(y2 - y1) || 1e-6;
      const t1 = Math.min(halfW[l.a] / dx, 26 / dy), t2 = Math.min(halfW[l.b] / dx, 26 / dy);
      const t = (t1 + 1 - t2) / 2;
      mx = x1 + (x2 - x1) * t; my = y1 + (y2 - y1) * t;
    }
    const color = MEDIUM_COLOR[l.medium] || "var(--muted)";
    const dist = l.distance_m >= 1000 ? `${fmt(l.distance_m / 1000)} km` : `${l.distance_m} m`;
    const label = `${l.medium === "Carrier circuit" ? (l.service.includes("IPsec") ? "IPsec" : "Carrier") : l.transceiver} · ${dist}`;
    const w = label.length * 6.6 + 12;
    return `<g><path d="${path}" fill="none" stroke="${color}" stroke-width="${l.role === "secondary" ? 2 : 3}" ${l.role === "secondary" ? 'stroke-dasharray="7 5"' : ""}/>
      <rect class="edge-label-bg" x="${mx - w / 2}" y="${my - 10}" width="${w}" height="19" rx="4"/>
      <text class="edge-label" x="${mx}" y="${my + 4}" text-anchor="middle">${esc(label)}</text></g>`;
  }).join("");
  const nodes = sites.map((s, i) => {
    const [x, y] = pos[s];
    const { title, sub, isCloud, w } = labelOf(s);
    return `<g class="node ${isCloud ? "cloud" : ""}" transform="translate(${x},${y})">
      <rect x="${-w / 2}" y="-26" width="${w}" height="52" rx="9" style="stroke:${SITE_COLORS[i % SITE_COLORS.length]}"/>
      <text text-anchor="middle" y="-6">${esc(title)}</text>
      <text class="sub" text-anchor="middle" y="15">${esc(sub)}</text></g>`;
  }).join("");
  const legend = Object.entries(MEDIUM_COLOR).map(([k, c]) => `<span><i class="swatch" style="background:${c}"></i>${esc(k)}</span>`).join("") +
    `<span><svg width="26" height="8"><line x1="0" y1="4" x2="26" y2="4" stroke="var(--muted)" stroke-width="2" stroke-dasharray="6 4"/></svg> secondary / backup</span>`;
  const sitesTbl = Object.entries(r.topology.sites).map(([s, d]) => `<tr><td>${esc(s)}</td><td class="num">${d.port_demand}</td><td class="num">${d.access_switches}</td><td class="num">${d.aps}</td><td class="num">${d.voice_phones}</td><td class="num">${fmt(d.poe_total_w)} W</td><td class="num">${fmt(d.poe_per_switch_w)} W</td></tr>`).join("");
  $("#tab-topology").innerHTML = `
    <div class="card topo"><h3>${esc(r.topology.tier)}</h3>
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Topology diagram">${edges}${nodes}</svg>
      <div class="legend">${legend}</div>
    </div>
    <div class="card"><h3>Access layer sizing &amp; PoE</h3><div class="table-wrap"><table>
      <thead><tr><th>Site</th><th class="num">Ports needed</th><th class="num">Access switches</th><th class="num">APs</th><th class="num">IP phones</th><th class="num">PoE total</th><th class="num">PoE / switch</th></tr></thead>
      <tbody>${sitesTbl}</tbody></table></div></div>
    <div class="card"><h3>Cabling plan</h3><div class="table-wrap"><table>
      <thead><tr><th>Device A</th><th>Port</th><th>Device B</th><th>Port</th><th>Medium</th></tr></thead>
      <tbody>${r.cabling.map((c) => `<tr><td>${esc(c.a)}</td><td class="mono">${esc(c.a_port)}</td><td>${esc(c.b)}</td><td class="mono">${esc(c.b_port)}</td><td>${esc(c.medium)}</td></tr>`).join("")}</tbody></table></div></div>`;
}

function budgetCell(b) {
  if (!b) return '<td class="muted">—</td><td></td>';
  const pct = Math.min(100, (b.total_with_margin_db / b.max_loss_db) * 100);
  const cls = b.headroom_db < 0.5 ? "warn" : "ok";
  return `<td class="num">${b.total_with_margin_db} / ${b.max_loss_db} dB</td>
          <td><div class="bar ${cls}" title="${b.headroom_db} dB headroom"><i style="width:${pct}%"></i></div><span class="small muted">${b.headroom_db} dB headroom${b.attenuator_needed ? " · attenuator" : ""}</span></td>`;
}

function renderMedia() {
  const r = state.result;
  const row = (l) => `<tr><td>${esc(l.subject)}</td>
    <td><i class="swatch" style="background:${MEDIUM_COLOR[l.medium] || "var(--muted)"}"></i>${esc(l.medium)}</td>
    <td>${esc(l.transceiver)}</td><td class="small muted">${esc(l.standard)}</td>
    <td class="num">${l.distance_m >= 1000 ? fmt(l.distance_m / 1000) + " km" : l.distance_m + " m"}</td>
    <td class="num">${l.bandwidth_gbps} G</td>${budgetCell(l.budget)}
    <td class="num">${l.latency_ms < 1 ? l.latency_ms.toFixed(4) : l.latency_ms.toFixed(1)}</td>
    <td>${l.role === "secondary" ? '<span class="pill">secondary</span>' : ""}${l.poe ? '<span class="pill accent">PoE</span>' : ""}${l.service ? `<span class="pill">${esc(l.service)}</span>` : ""}</td></tr>`;
  const head = `<thead><tr><th>Link / run</th><th>Medium</th><th>Transceiver</th><th>Standard</th><th class="num">Distance</th><th class="num">BW</th><th class="num">Loss / budget</th><th>Headroom</th><th class="num">One-way ms</th><th></th></tr></thead>`;
  const why = r.rationale.filter((e) => e.domain === "L1 Media");
  $("#tab-media").innerHTML = `
    <div class="card"><h3>Inter-site links</h3><div class="table-wrap"><table>${head}<tbody>${r.media.links.map(row).join("")}</tbody></table></div></div>
    ${r.media.cable_runs.length ? `<div class="card"><h3>Intra-building cable runs</h3><div class="table-wrap"><table>${head}<tbody>${r.media.cable_runs.map(row).join("")}</tbody></table></div></div>` : ""}
    <div class="card"><h3>Why these media?</h3>${why.map(ratCard).join("")}</div>`;
}

function renderAddressing() {
  const r = state.result, a = r.addressing;
  const rootSize = a.root_size;
  const [rootNet] = a.root.split("/");
  const ipInt = (s) => s.split(".").reduce((x, o) => x * 256 + Number(o), 0);
  const base = ipInt(rootNet);
  const inRoot = a.blocks.filter((b) => { const n = ipInt(b.block.split("/")[0]); return n >= base && n < base + rootSize; });
  let cursor = base;
  const segs = [];
  inRoot.sort((x, y) => ipInt(x.block.split("/")[0]) - ipInt(y.block.split("/")[0])).forEach((b, i) => {
    const n = ipInt(b.block.split("/")[0]);
    if (n > cursor) segs.push(`<div style="flex:${n - cursor}" title="free"></div>`);
    segs.push(`<div style="flex:${b.root_size};background:${SITE_COLORS[i % SITE_COLORS.length]}" title="${esc(b.site)} ${esc(b.block)}">${b.root_size / rootSize > 0.04 ? esc(b.site) : ""}</div>`);
    cursor = n + b.root_size;
  });
  const blocks = a.blocks.map((b, i) => `
    <div class="card"><h3><i class="swatch" style="background:${SITE_COLORS[i % SITE_COLORS.length]}"></i>${esc(b.site)} <span class="mono muted">${esc(b.block)}</span>
      <span class="pill">${b.root_utilization_pct}% used</span> <span class="pill">wildcard ${esc(b.wildcard)}</span></h3>
      <div class="table-wrap"><table><thead><tr><th>Subnet</th><th class="num">VLAN</th><th class="num">Hosts</th><th>CIDR</th><th>Mask</th><th>Wildcard</th><th>Gateway</th><th>Range</th><th>Broadcast</th><th>Utilisation</th></tr></thead><tbody>
      ${b.subnets.map((s) => `<tr><td>${esc(s.name)} <span class="small muted">${esc(s.kind === "lan" ? s.role : s.kind)}</span></td><td class="num">${s.vlan_id ?? "—"}</td><td class="num">${fmt(s.hosts_requested)}</td>
        <td class="mono">${esc(s.cidr)}</td><td class="mono">${esc(s.mask)}</td><td class="mono">${esc(s.wildcard)}</td><td class="mono">${esc(s.gateway ?? "—")}</td>
        <td class="mono small">${esc(s.first_usable)} – ${esc(s.last_usable)}</td><td class="mono">${esc(s.broadcast)}</td>
        <td><div class="bar ${s.utilization_pct < 40 ? "warn" : "ok"}"><i style="width:${Math.min(100, s.utilization_pct)}%"></i></div><span class="small muted">${s.utilization_pct}% of ${fmt(s.usable)}</span></td></tr>`).join("")}
      </tbody></table></div></div>`).join("");
  $("#tab-addressing").innerHTML = `
    <div class="kpis">${kpi(esc(a.root), "root prefix")}${kpi(a.root_utilization_pct + "%", "root consumed by site blocks")}${kpi(a.address_efficiency_pct + "%", "host demand / allocated")}${kpi(fmt(a.vlsm_addresses), "addresses with VLSM")}${kpi(fmt(a.flsm_equivalent_addresses), "addresses with fixed-length")}</div>
    <div class="card"><h3>Address map of ${esc(a.root)}</h3><div class="addr-map">${segs.join("")}<div style="flex:${base + rootSize - cursor}" title="free"></div></div>
      <div class="legend"><span>Each site gets one contiguous, bit-aligned block so it can be summarised as a single route. Hatched = free.</span></div></div>
    ${blocks}`;
}

function renderRouting() {
  const r = state.result, rt = r.routing;
  const areas = Object.entries(rt.areas).map(([s, a]) => {
    const sm = rt.summaries[s];
    return `<tr><td>${esc(s)}</td><td class="num">${a}</td><td class="mono">${sm ? esc(`area ${sm.area} range ${sm.network} ${sm.mask}`) : "—"}</td></tr>`;
  }).join("");
  const lat = r.latency.pairs.map((p) => `<tr><td>${esc(p.a)} ↔ ${esc(p.b)}${p.failover_of ? ' <span class="pill warn">failover</span>' : ""}</td><td>${esc(p.path.join(" → "))}</td><td class="num">${p.one_way_ms}</td><td>${p.within_budget === undefined ? "" : p.within_budget ? '<span class="pill ok">within</span>' : '<span class="pill bad">exceeds</span>'}</td></tr>`).join("");
  const qos = r.qos ? `<div class="card"><h3>QoS classes (hierarchical shaper → LLQ)</h3><div class="table-wrap"><table><thead><tr><th>Class</th><th>DSCP</th><th>Treatment</th><th class="num">Share</th></tr></thead><tbody>
      ${r.qos.classes.map((c) => `<tr><td>${esc(c.name)}</td><td class="mono">${esc(c.dscp.toUpperCase())}</td><td>${c.priority ? "strict priority (LLQ)" : "CBWFQ minimum"}</td><td class="num">${c.percent}%</td></tr>`).join("")}
      <tr><td>class-default</td><td class="mono">BE</td><td>fair-queue</td><td class="num">remainder</td></tr></tbody></table></div></div>` : "";
  $("#tab-routing").innerHTML = `
    <div class="grid-2">
      <div class="card"><h3>${esc(rt.design)}</h3><dl class="facts">
        <dt>IGP</dt><dd>${esc(rt.igp)} process ${rt.process_id}</dd>
        <dt>Subnets</dt><dd>${rt.subnet_count} (threshold 50)</dd>
        <dt>Backbone hub</dt><dd>${esc(rt.hub)}</dd>
        <dt>Reference BW</dt><dd>${fmt(rt.reference_bandwidth_mbps)} Mbps</dd>
        <dt>BFD</dt><dd>${rt.bfd ? "50 ms × 3 (150 ms detection)" : "not required"}</dd>
        <dt>eBGP</dt><dd>${rt.bgp ? `AS${rt.bgp.asn} ↔ ${rt.bgp.peers.map((p) => `AS${p.asn} (${esc(p.site)}, ${esc(p.prefix)})`).join(", ")}; advertises ${esc(rt.bgp.advertise.join(", "))}` : "none (single AS)"}</dd>
      </dl></div>
      <div class="card"><h3>OSPF areas &amp; ABR summaries</h3><div class="table-wrap"><table><thead><tr><th>Site</th><th class="num">Area</th><th>Summary at ABR</th></tr></thead><tbody>${areas}</tbody></table></div></div>
    </div>
    ${qos}
    <div class="card"><h3>Path latency (Dijkstra on one-way delay)</h3><div class="table-wrap"><table><thead><tr><th>Pair</th><th>Path</th><th class="num">ms</th><th></th></tr></thead><tbody>${lat}</tbody></table></div></div>
    <div class="card"><h3>Why this routing design?</h3>${r.rationale.filter((e) => e.domain === "L3 Routing" || e.domain === "QoS & Latency").map(ratCard).join("")}</div>`;
}

function highlight(cfg) {
  return esc(cfg).split("\n").map((line) => {
    if (/^\s*!/.test(line)) return `<span class="c">${line}</span>`;
    return line
      .replace(/\b(\d{1,3}(?:\.\d{1,3}){3})\b/g, '<span class="ip">$1</span>')
      .replace(/^(\s*)(interface|router|hostname|vlan|ip|crypto|line|policy-map|class-map|class|neighbor|network|area|switchport|spanning-tree|tunnel|encapsulation|service-policy|access-class|permit|deny|remark|bfd|priority|bandwidth|shape|redistribute|route-map|match|set)\b/, '$1<span class="k">$2</span>');
  }).join("\n");
}

function combinedExport() {
  const r = state.result;
  const lines = [`! NetArchitect v${r.version} export - ${r.meta.name}`, `! Topology: ${r.topology.tier} | Routing: ${r.routing.design}`, "!", "! CABLING PLAN"];
  r.cabling.forEach((c) => lines.push(`!   ${c.a} ${c.a_port} <-> ${c.b} ${c.b_port}  (${c.medium})`));
  for (const [n, cfg] of Object.entries(r.configs)) lines.push("", "!".repeat(72), `! DEVICE: ${n}`, "!".repeat(72), cfg);
  return lines.join("\n");
}

function download(name, text) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
  a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

function deviceKind(cfg) {
  const m = cfg.match(/^! Platform : (.*)$/m);
  return m ? m[1].replace(/^Cisco /, "").split(" (")[0].split(" / ")[0] : "";
}

function renderConfigs() {
  const r = state.result;
  const names = Object.keys(r.configs);
  if (!names.includes(state.device)) state.device = names[0];
  const cfg = r.configs[state.device];
  $("#tab-configs").innerHTML = `
    <div class="cfg-layout">
      <div class="dev-list">${names.map((n) => `<button data-dev="${esc(n)}" class="${n === state.device ? "active" : ""}"><span>${esc(n)}</span><span class="kind">${esc(deviceKind(r.configs[n]))}</span></button>`).join("")}</div>
      <div>
        <div class="cfg-actions">
          <b>${esc(state.device)}</b><span class="muted small">${cfg.split("\n").length} lines</span>
          <span style="flex:1"></span>
          <button id="copyCfg">Copy</button>
          <button id="dlCfg">Download .cfg</button>
          <button id="dlAll" class="primary">Download all (${names.length})</button>
        </div>
        <pre class="code">${highlight(cfg)}</pre>
      </div>
    </div>`;
  $$("#tab-configs .dev-list button").forEach((b) => b.addEventListener("click", () => { state.device = b.dataset.dev; renderConfigs(); }));
  $("#copyCfg").addEventListener("click", async (e) => {
    try { await navigator.clipboard.writeText(cfg); e.target.textContent = "Copied ✓"; }
    catch { e.target.textContent = "Copy failed"; }
    setTimeout(() => (e.target.textContent = "Copy"), 1500);
  });
  $("#dlCfg").addEventListener("click", () => download(`${state.device}.cfg`, cfg));
  $("#dlAll").addEventListener("click", () => download(`${r.meta.profile}_configs.txt`, combinedExport()));
}

function ratCard(e) {
  return `<div class="card rat ${e.level === "warning" ? "warning" : ""}">
    <div class="head"><span class="pill ${e.level === "warning" ? "warn" : "accent"}">${esc(e.domain)}</span><b>${esc(e.subject)}</b><span class="decision">→ ${esc(e.decision)}</span></div>
    <p>${esc(e.justification)}</p>
    ${e.references.length ? `<div class="refs">${e.references.map((x) => `<span class="pill">${esc(x)}</span>`).join("")}</div>` : ""}
  </div>`;
}

function renderRationale() {
  const r = state.result;
  const domains = ["All", ...new Set(r.rationale.map((e) => e.domain))];
  if (!domains.includes(state.domain)) state.domain = "All";
  const q = state.search.toLowerCase();
  const list = r.rationale.filter((e) => (state.domain === "All" || e.domain === state.domain) &&
    (!q || `${e.subject} ${e.decision} ${e.justification} ${e.references.join(" ")}`.toLowerCase().includes(q)));
  $("#tab-rationale").innerHTML = `
    <div class="filters">${domains.map((d) => `<button data-d="${esc(d)}" class="${d === state.domain ? "active" : ""}">${esc(d)} <span class="small">${d === "All" ? r.rationale.length : r.rationale.filter((e) => e.domain === d).length}</span></button>`).join("")}
      <input id="ratSearch" type="search" placeholder="Search justifications, RFCs, subnets…" value="${esc(state.search)}">
      <button id="dlRat" class="ghost">Export log</button></div>
    <div class="panel">${list.map(ratCard).join("") || '<p class="muted">No entries match.</p>'}</div>`;
  $$("#tab-rationale .filters button[data-d]").forEach((b) => b.addEventListener("click", () => { state.domain = b.dataset.d; renderRationale(); }));
  const s = $("#ratSearch");
  s.addEventListener("input", () => { state.search = s.value; const pos = s.selectionStart; renderRationale(); const n = $("#ratSearch"); n.focus(); n.setSelectionRange(pos, pos); });
  $("#dlRat").addEventListener("click", () => download(`${r.meta.profile}_rationale.txt`, r.rationale_text));
}

function renderVerify() {
  const v = state.result.verification;
  $("#tab-verify").innerHTML = `
    <div class="kpis">${kpi(`${v.passed}/${v.total}`, "checks passed")}${kpi(v.checks.filter((c) => c.type === "lpm").length, "LPM overlap probes")}${kpi(v.checks.filter((c) => c.type === "acl").length, "ACL packet walks")}</div>
    <div class="card"><h3>Packet-flow simulation</h3><p class="muted small">Longest-prefix match proves each LAN resolves to exactly one subnet; ACL walks evaluate the generated access lists entry-by-entry with the router's wildcard arithmetic.</p>
    <div class="table-wrap"><table><thead><tr><th>Type</th><th>Object</th><th>Flow</th><th>Expected</th><th>Result</th><th class="num">Entry</th><th></th></tr></thead><tbody>
    ${v.checks.map((c) => `<tr><td>${esc(c.type.toUpperCase())}</td><td class="mono">${esc(c.acl || "routing table")}</td><td class="mono small">${esc(c.flow)}</td><td>${esc(c.expected)}</td><td>${esc(c.result)}</td><td class="num">${c.matched_entry ?? (c.type === "acl" ? "implicit" : "")}</td><td>${c.pass ? '<span class="pill ok">pass</span>' : '<span class="pill bad">fail</span>'}</td></tr>`).join("")}
    </tbody></table></div></div>`;
}

/* ---------------------------------------------------------------- tools */
async function toolMedia() {
  const out = $("#tMediaOut");
  try {
    const d = await api("/api/media", { distance_m: Number($("#tDist").value), bandwidth_gbps: Number($("#tBw").value),
      preference: $("#tPref").value, transport: $("#tTrans").value, poe: $("#tPoe").checked });
    out.innerHTML = `<div class="result"><i class="swatch" style="background:${MEDIUM_COLOR[d.decision.medium]}"></i>${esc(d.decision.medium)} · ${esc(d.decision.transceiver)}</div>${d.rationale.map(ratCard).join("")}`;
  } catch (e) { out.innerHTML = `<div class="error-box">${errorHtml(e.data || { message: e.message })}</div>`; }
}

async function toolVlsm() {
  const out = $("#tVlsmOut");
  try {
    const hosts = $("#vHosts").value.split(/[,\s]+/).filter(Boolean).map(Number);
    const d = await api("/api/vlsm", { root: $("#vRoot").value.trim(), hosts, p2p: Number($("#vP2p").value), p2p_prefix: Number($("#vP2pPre").value) });
    out.innerHTML = `<div class="result">${fmt(d.allocated)} / ${fmt(d.root_size)} addresses (${d.root_utilization_pct}%)</div>
      <div class="table-wrap"><table><thead><tr><th>Name</th><th class="num">Hosts</th><th>CIDR</th><th>Gateway</th><th>Broadcast</th><th>Wildcard</th></tr></thead><tbody>
      ${d.subnets.map((s) => `<tr><td>${esc(s.name)}</td><td class="num">${s.hosts_requested}</td><td class="mono">${esc(s.cidr)}</td><td class="mono">${esc(s.gateway ?? s.first_usable)}</td><td class="mono">${esc(s.broadcast)}</td><td class="mono">${esc(s.wildcard)}</td></tr>`).join("")}
      </tbody></table></div>`;
  } catch (e) { out.innerHTML = `<div class="error-box">${errorHtml(e.data || { message: e.message })}</div>`; }
}

async function toolWildcard() {
  const out = $("#tWcOut");
  try {
    const d = await api("/api/wildcard", { cidr: $("#wCidr").value.trim() });
    out.innerHTML = `<dl class="facts mono"><dt>Network</dt><dd>${esc(d.network)}</dd><dt>Mask</dt><dd>${esc(d.mask)}</dd><dt>Wildcard</dt><dd><b>${esc(d.wildcard)}</b></dd><dt>Broadcast</dt><dd>${esc(d.broadcast)}</dd><dt>Usable</dt><dd>${fmt(d.usable)}</dd></dl>`;
  } catch (e) { out.innerHTML = `<div class="error-box">${errorHtml(e.data || { message: e.message })}</div>`; }
}

/* ------------------------------------------------------------- wiring */
function showTab(name) {
  $$("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  $$(".panel").forEach((p) => { if (p.parentElement.classList.contains("content")) p.hidden = p.id !== `tab-${name}`; });
  $("#empty").hidden = !!state.result || name === "tools";
  if (!state.result && name !== "tools") $$(".content > .panel").forEach((p) => (p.hidden = true));
  try { localStorage.setItem("na-tab", name); } catch { /* storage unavailable */ }
}

function initTheme() {
  let saved = null;
  try { saved = localStorage.getItem("na-theme"); } catch { /* ignore */ }
  if (saved) document.documentElement.dataset.theme = saved;
  $("#themeBtn").addEventListener("click", () => {
    const dark = document.documentElement.dataset.theme
      ? document.documentElement.dataset.theme === "dark"
      : matchMedia("(prefers-color-scheme: dark)").matches;
    const next = dark ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("na-theme", next); } catch { /* ignore */ }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  $$("#tabs button").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));
  $("#runBtn").addEventListener("click", run);
  $("#paramEditor").addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") run(); });
  $("#formatBtn").addEventListener("click", () => {
    try { $("#paramEditor").value = JSON.stringify(JSON.parse($("#paramEditor").value), null, 2); showError(null); }
    catch (e) { showError({ error: "InvalidJSON", message: e.message }); }
  });
  $("#resetBtn").addEventListener("click", () => selectPreset(state.presetId === "custom" ? "campus_lan" : state.presetId));
  $("#fileInput").addEventListener("change", async (e) => {
    const f = e.target.files[0]; if (!f) return;
    $("#paramEditor").value = await f.text();
    $$("#presetCards .preset-card").forEach((b) => b.classList.toggle("active", b.dataset.id === "custom"));
    state.presetId = "custom"; e.target.value = ""; run();
  });
  $("#tMediaBtn").addEventListener("click", toolMedia);
  $("#tVlsmBtn").addEventListener("click", toolVlsm);
  $("#tWcBtn").addEventListener("click", toolWildcard);
  let tab = "overview";
  try { tab = localStorage.getItem("na-tab") || "overview"; } catch { /* ignore */ }
  showTab(tab);
  loadPresets().catch((e) => { showError({ error: "Startup", message: e.message }); setStatus("Server unreachable", "bad"); });
});
