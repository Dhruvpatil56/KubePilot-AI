def get_dashboard_html() -> str:
    return r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>KubePilot AI — Dashboard</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background: #0a0f1e;
      color: #c9d1d9;
      font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
      font-size: 14px;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* ── refresh bar ── */
    #rbar {
      height: 3px;
      background: linear-gradient(90deg, #00d4ff, #00ff88, #00d4ff);
      background-size: 200% 100%;
      transform-origin: left;
      animation: shrink 30s linear infinite;
      flex-shrink: 0;
    }
    @keyframes shrink { from { transform: scaleX(1); } to { transform: scaleX(0); } }

    /* ── header ── */
    header {
      background: #0d1526;
      padding: 14px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-shrink: 0;
      position: relative;
    }
    header::after {
      content: '';
      position: absolute;
      bottom: 0; left: 0; right: 0; height: 1px;
      background: linear-gradient(90deg, transparent, #00d4ff 25%, #00ff88 75%, transparent);
    }
    .logo-row { display: flex; align-items: center; gap: 12px; }
    .logo {
      color: #00d4ff;
      font-size: 1.6rem;
      font-weight: 700;
      letter-spacing: 2px;
      text-shadow: 0 0 20px rgba(0,212,255,0.6), 0 0 40px rgba(0,212,255,0.2);
    }
    .ver-badge {
      background: #0a0f1e;
      border: 1px solid #00d4ff;
      color: #00d4ff;
      font-size: 10px;
      padding: 3px 12px;
      border-radius: 20px;
      box-shadow: 0 0 8px rgba(0,212,255,0.25);
    }
    .live-dot {
      display: inline-flex; align-items: center; gap: 7px;
      font-size: 11px; color: #00ff88; letter-spacing: 1px; font-weight: 600;
    }
    .live-dot::before {
      content: ''; width: 10px; height: 10px; background: #00ff88;
      border-radius: 50%; display: inline-block;
      animation: pulse 1.5s ease-in-out infinite;
      box-shadow: 0 0 8px #00ff88;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; box-shadow: 0 0 6px #00ff88, 0 0 14px rgba(0,255,136,0.4); transform: scale(1); }
      50%       { opacity: 0.55; box-shadow: 0 0 3px #00ff88; transform: scale(0.82); }
    }
    .hdr-right { display: flex; align-items: center; gap: 22px; font-size: 12px; color: #8b949e; }
    .hdr-right span { color: #c9d1d9; }

    /* ── health bar ── */
    #health-bar {
      background: #0d1526;
      border-bottom: 1px solid #1e3a5f;
      padding: 9px 28px;
      display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
      flex-shrink: 0; font-size: 12px;
    }
    .hb-pill {
      display: inline-flex; align-items: center; gap: 6px;
      color: #8b949e; padding: 4px 12px; border-radius: 20px;
      background: #0a0f1e; border: 1px solid #1e3a5f;
    }
    .hb-pill .val { color: #c9d1d9; }
    .hb-dot {
      width: 7px; height: 7px; border-radius: 50%; display: inline-block; flex-shrink: 0;
    }
    .hb-online { background: #00ff88; box-shadow: 0 0 5px #00ff88; }
    .hb-err    { background: #ff4444; box-shadow: 0 0 5px #ff4444; }
    .hb-warn   { background: #ffaa00; box-shadow: 0 0 5px #ffaa00; }
    .hb-info   { background: #00d4ff; box-shadow: 0 0 5px #00d4ff; }
    .hb-sep { color: #1e3a5f; user-select: none; padding: 0 2px; }

    /* ── layout ── */
    main { flex: 1; padding: 24px 28px; max-width: 1600px; width: 100%; margin: 0 auto; }
    .layout { display: flex; gap: 22px; align-items: flex-start; }
    .primary { flex: 1; min-width: 0; }
    .sidebar { width: 295px; flex-shrink: 0; }

    /* ── stat cards ── */
    .stats { display: flex; gap: 16px; margin-bottom: 22px; flex-wrap: wrap; }
    .stat-card {
      border: 1px solid #1e3a5f;
      border-radius: 10px;
      padding: 22px 24px;
      flex: 1; min-width: 130px;
      position: relative; overflow: hidden;
      transition: transform 0.15s, box-shadow 0.15s;
      cursor: default;
    }
    .stat-card::before {
      content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    }
    .stat-card.c-total { background: linear-gradient(135deg, #0d1526 55%, #0d1a32); }
    .stat-card.c-ok    { background: linear-gradient(135deg, #0d1526 55%, #0d1e16); }
    .stat-card.c-dry   { background: linear-gradient(135deg, #0d1526 55%, #0d1e28); }
    .stat-card.c-err   { background: linear-gradient(135deg, #0d1526 55%, #1c0e0e); }
    .stat-card.c-total::before { background: linear-gradient(90deg, #58a6ff, #00d4ff); }
    .stat-card.c-ok::before    { background: linear-gradient(90deg, #3fb950, #00ff88); }
    .stat-card.c-dry::before   { background: linear-gradient(90deg, #00d4ff, #00ff88); }
    .stat-card.c-err::before   { background: linear-gradient(90deg, #f85149, #ff4444); }
    .stat-card.c-total:hover { transform: translateY(-3px); box-shadow: 0 8px 28px rgba(88,166,255,0.25); }
    .stat-card.c-ok:hover    { transform: translateY(-3px); box-shadow: 0 8px 28px rgba(0,255,136,0.2); }
    .stat-card.c-dry:hover   { transform: translateY(-3px); box-shadow: 0 8px 28px rgba(0,212,255,0.25); }
    .stat-card.c-err:hover   { transform: translateY(-3px); box-shadow: 0 8px 28px rgba(248,81,73,0.25); }
    .stat-icon { font-size: 20px; margin-bottom: 8px; }
    .stat-label { color: #8b949e; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 4px; }
    .stat-value { font-size: 4rem; font-weight: 700; line-height: 1; margin-top: 4px; }
    .stat-card.c-total .stat-value { color: #58a6ff; }
    .stat-card.c-ok    .stat-value { color: #3fb950; }
    .stat-card.c-dry   .stat-value { color: #00d4ff; }
    .stat-card.c-err   .stat-value { color: #f85149; }

    /* ── table ── */
    .table-wrap { background: #0d1526; border: 1px solid #1e3a5f; border-radius: 10px; overflow: hidden; }
    table { width: 100%; border-collapse: collapse; }
    thead { background: #0a0f1e; }
    th {
      padding: 12px 16px; text-align: left; color: #8b949e;
      font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1.2px;
      border-bottom: 1px solid #1e3a5f; white-space: nowrap;
    }
    tbody tr.data-row {
      border-bottom: 1px solid #1a2a3a;
      cursor: pointer;
      transition: background 0.1s, border-left-color 0.1s;
      border-left: 3px solid transparent;
    }
    tbody tr.data-row:last-of-type { border-bottom: none; }
    tbody tr.data-row:hover { background: #0f1f38; border-left-color: #00d4ff; }
    tbody tr.data-row.expanded { border-left-color: #00d4ff; background: #0f1f38; }
    td { padding: 13px 16px; vertical-align: middle; font-size: 0.95rem; }
    .chev { display: inline-block; transition: transform 0.2s; color: #8b949e; margin-right: 7px; font-style: normal; font-size: 12px; }
    tr.data-row.expanded .chev { transform: rotate(90deg); color: #00d4ff; }
    .pod-name { font-family: 'JetBrains Mono', 'Fira Code', monospace; color: #e6edf3; letter-spacing: -0.3px; }

    /* ── badges ── */
    .badge {
      display: inline-flex; align-items: center; gap: 4px;
      padding: 3px 11px; border-radius: 20px;
      font-size: 10px; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.5px; white-space: nowrap;
    }
    .bd-red    { background: #ff4444; color: #fff; border: none; box-shadow: 0 0 8px rgba(255,68,68,0.55); }
    .bd-yellow { background: #ffaa00; color: #000; border: none; box-shadow: 0 0 8px rgba(255,170,0,0.55); }
    .bd-green  { background: #1a3a1a; color: #3fb950; border: 1px solid #2a5a2a; }
    .bd-blue   { background: #00d4ff; color: #0a0f1e; border: none; box-shadow: 0 0 8px rgba(0,212,255,0.45); }
    .bd-gray   { background: #1a2233; color: #8b949e; border: 1px solid #1e3a5f; }

    /* ── confidence bar ── */
    .cbar { display: flex; align-items: center; gap: 8px; min-width: 85px; }
    .cbar-bg { flex: 1; height: 10px; background: #1a2233; border-radius: 5px; overflow: hidden; }
    .cbar-fill { height: 100%; border-radius: 5px; background: linear-gradient(90deg, #00d4ff, #00ff88); box-shadow: 0 0 6px rgba(0,212,255,0.4); }
    .cbar-pct { font-size: 11px; font-weight: 700; min-width: 32px; text-align: right; }

    /* ── RCA expand ── */
    tr.rca-row { display: none; }
    tr.rca-row.open { display: table-row; }
    .rca-cell { padding: 0 16px 16px 32px !important; }
    .rca-box {
      background: #0a0f1e; border: 1px solid #1e3a5f; border-radius: 6px;
      padding: 16px 20px;
      display: grid; grid-template-columns: 1fr 1fr; gap: 12px 24px;
      animation: slideIn 0.15s ease;
    }
    @keyframes slideIn { from { opacity: 0; transform: translateY(-5px); } to { opacity: 1; transform: translateY(0); } }
    .rf { display: flex; flex-direction: column; gap: 4px; }
    .rf.full { grid-column: 1 / -1; }
    .rk { color: #8b949e; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 1.2px; }
    .rv { color: #c9d1d9; line-height: 1.6; font-size: 0.9rem; }

    /* ── sidebar panel ── */
    .panel { background: #0d1526; border: 1px solid #1e3a5f; border-radius: 10px; overflow: hidden; }
    .panel-hdr {
      background: #0a0f1e; padding: 12px 16px;
      border-bottom: 1px solid #1e3a5f;
      font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 1.2px; color: #c9d1d9;
    }
    .panel-body { padding: 14px 16px; }
    .feed-item { display: flex; gap: 12px; padding: 11px 0; border-bottom: 1px solid #1a2233; }
    .feed-item:last-child { border-bottom: none; }
    .fdot { width: 10px; height: 10px; border-radius: 50%; margin-top: 4px; flex-shrink: 0; }
    .fdot.red    { background: #ff4444; box-shadow: 0 0 6px rgba(255,68,68,0.6); }
    .fdot.green  { background: #00ff88; box-shadow: 0 0 6px rgba(0,255,136,0.6); }
    .fdot.yellow { background: #ffaa00; box-shadow: 0 0 6px rgba(255,170,0,0.6); }
    .fdot.blue   { background: #00d4ff; box-shadow: 0 0 6px rgba(0,212,255,0.6); }
    .fdot.gray   { background: #8b949e; }
    .fcontent { flex: 1; min-width: 0; }
    .ftime   { color: #4a5568; font-size: 0.7rem; margin-bottom: 3px; }
    .falert  { color: #e6edf3; font-size: 0.875rem; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-bottom: 3px; }
    .faction { color: #8b949e; font-size: 0.75rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .feed-empty { color: #8b949e; font-size: 12px; text-align: center; padding: 26px 0; }

    /* ── empty state ── */
    .empty { text-align: center; padding: 60px 24px; color: #8b949e; }
    .empty pre { font-size: 12px; line-height: 1.4; color: #1e3a5f; margin-bottom: 20px; display: inline-block; text-align: left; }
    .empty p { font-size: 15px; }

    /* ── footer ── */
    footer {
      background: #0d1526; border-top: 1px solid #1e3a5f;
      padding: 10px 28px; display: flex; align-items: center; justify-content: space-between;
      font-size: 11px; color: #8b949e; flex-shrink: 0;
    }
    .fsep { color: #1e3a5f; margin: 0 8px; }
  </style>
</head>
<body>
  <div id="rbar"></div>

  <header>
    <div class="logo-row">
      <div class="logo">&#9096; KubePilot AI</div>
      <span class="ver-badge">v2.0.0</span>
      <span class="live-dot">LIVE</span>
    </div>
    <div class="hdr-right">
      <div>Incidents: <span id="hdr-total">&#8212;</span></div>
      <div>Updated: <span id="hdr-updated">&#8212;</span></div>
    </div>
  </header>

  <div id="health-bar">
    <div class="hb-pill"><span class="hb-dot hb-online"></span>Agent <span class="val">Online</span></div>
    <span class="hb-sep">|</span>
    <div class="hb-pill">LLM: <span class="val" id="hb-llm">&#8212;</span></div>
    <span class="hb-sep">|</span>
    <div class="hb-pill">Dry Run: <span class="val" id="hb-dry">&#8212;</span></div>
    <span class="hb-sep">|</span>
    <div class="hb-pill">Namespace: <span class="val" id="hb-ns">&#8212;</span></div>
    <span class="hb-sep">|</span>
    <div class="hb-pill">K8s: <span class="val" id="hb-k8s">&#8212;</span></div>
  </div>

  <main>
    <div class="layout">
      <div class="primary">
        <div class="stats">
          <div class="stat-card c-total">
            <div class="stat-icon">&#9889;</div>
            <div class="stat-label">Total Incidents</div>
            <div class="stat-value" id="s-total">&#8212;</div>
          </div>
          <div class="stat-card c-ok">
            <div class="stat-icon">&#128202;</div>
            <div class="stat-label">Remediated</div>
            <div class="stat-value" id="s-remediated">&#8212;</div>
          </div>
          <div class="stat-card c-dry">
            <div class="stat-icon">&#128295;</div>
            <div class="stat-label">Dry Run</div>
            <div class="stat-value" id="s-dryrun">&#8212;</div>
          </div>
          <div class="stat-card c-err">
            <div class="stat-icon">&#10060;</div>
            <div class="stat-label">Errors</div>
            <div class="stat-value" id="s-errors">&#8212;</div>
          </div>
        </div>
        <div id="content">
          <div class="empty"><p>Loading incidents&#8230;</p></div>
        </div>
      </div>

      <div class="sidebar">
        <div class="panel">
          <div class="panel-hdr">&#9201; Activity Feed</div>
          <div class="panel-body" id="feed-body">
            <div class="feed-empty">No activity yet</div>
          </div>
        </div>
      </div>
    </div>
  </main>

  <footer>
    <div>KubePilot AI v2.0</div>
    <div>
      <span>Powered by LangGraph + <span id="ft-llm">Groq</span></span>
      <span class="fsep">|</span>
      <span>Total processed: <span id="ft-total">0</span></span>
    </div>
  </footer>

  <script>
    // ── helpers ──────────────────────────────────────────────────────────
    function esc(s) {
      return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }

    function timeAgo(ts) {
      if (!ts) return '—';
      try {
        const d = new Date(ts.endsWith('Z') ? ts : ts + 'Z');
        const s = Math.floor((Date.now() - d) / 1000);
        if (s < 60) return s + 's ago';
        if (s < 3600) return Math.floor(s/60) + 'm ago';
        if (s < 86400) return Math.floor(s/3600) + 'h ago';
        return Math.floor(s/86400) + 'd ago';
      } catch(_) { return ts; }
    }

    function fmtTs(ts) {
      if (!ts) return '—';
      try { return new Date(ts.endsWith('Z') ? ts : ts+'Z').toLocaleString(); }
      catch(_) { return ts; }
    }

    function severityIcon(alert) {
      const a = (alert||'').toLowerCase();
      if (a.includes('crash')||a.includes('oom')||a.includes('critical')) return '🔴';
      if (a.includes('notready')||a.includes('warning')||a.includes('slow')) return '🟡';
      if (a.includes('info')) return '🔵';
      return '🟡';
    }

    function alertBadge(alert) {
      const a = (alert||'').toLowerCase();
      let cls = 'bd-gray';
      if (a.includes('crash')||a.includes('oom')||a.includes('critical')) cls = 'bd-red';
      else if (a.includes('notready')||a.includes('warning')||a.includes('slow')) cls = 'bd-yellow';
      return `<span class="badge ${cls}">${severityIcon(alert)} ${esc(alert||'—')}</span>`;
    }

    function statusBadge(status, action) {
      const act = action || '';
      if (act.startsWith('dry_run'))      return '<span class="badge bd-blue">🔧 dry run</span>';
      if (status === 'remediated')         return '<span class="badge bd-green">✅ remediated</span>';
      if (status === 'error')              return '<span class="badge bd-red">❌ error</span>';
      if (status === 'analyzed')           return '<span class="badge bd-yellow">📋 analyzed</span>';
      if (status === 'escalated')          return '<span class="badge bd-red">🔺 escalated</span>';
      if (status === 'suppressed')         return '<span class="badge bd-gray">🔕 suppressed</span>';
      if (status === 'investigating')      return '<span class="badge bd-gray">🔍 investigating</span>';
      return `<span class="badge bd-gray">${esc(status)}</span>`;
    }

    function confBar(rca) {
      if (!rca || rca.confidence == null) return '<span style="color:#8b949e">—</span>';
      const pct = Math.round(rca.confidence * 100);
      const col = pct >= 70 ? '#00d4ff' : pct >= 40 ? '#ffaa00' : '#ff4444';
      return `<div class="cbar">
        <div class="cbar-bg"><div class="cbar-fill" style="width:${pct}%"></div></div>
        <span class="cbar-pct" style="color:${col}">${pct}%</span>
      </div>`;
    }

    function rcaHtml(rca) {
      if (!rca) return '<em style="color:#8b949e">No RCA data</em>';
      const f = (k,v,full) => v != null
        ? `<div class="rf${full?' full':''}"><div class="rk">${k}</div><div class="rv">${esc(v)}</div></div>`
        : '';
      return `<div class="rca-box">
        ${f('Root Cause', rca.root_cause, true)}
        ${f('Reasoning', rca.reasoning, true)}
        ${f('Recommended Action', rca.recommended_action, false)}
        ${f('Risk Level', rca.risk_level, false)}
        ${f('Confidence', rca.confidence != null ? Math.round(rca.confidence*100)+'%' : null, false)}
      </div>`;
    }

    function feedDot(inc) {
      const act = inc.action_taken || '';
      if (inc.status === 'error') return 'red';
      if (inc.status === 'remediated') return 'green';
      if (act.startsWith('dry_run')) return 'blue';
      if (inc.status === 'analyzed') return 'yellow';
      return 'gray';
    }

    function renderFeed(incidents) {
      const el = document.getElementById('feed-body');
      const items = incidents.slice(0, 5);
      if (!items.length) { el.innerHTML = '<div class="feed-empty">No activity yet</div>'; return; }
      el.innerHTML = items.map(inc => `
        <div class="feed-item">
          <div class="fdot ${feedDot(inc)}"></div>
          <div class="fcontent">
            <div class="ftime">${esc(timeAgo(inc.timestamp))}</div>
            <div class="falert">${esc(inc.alert || '—')}</div>
            <div class="faction">${esc(inc.action_taken || inc.status || '—')}</div>
          </div>
        </div>`).join('');
    }

    const ROBOT = `  ┌────────────────┐
  │  (ʘ‿ʘ)  K8S   │
  │  <( )>  OK    │
  │   / \\         │
  └────────────────┘`;

    // ── render ───────────────────────────────────────────────────────────
    function render(data) {
      const incidents = data.incidents || [];
      const total = data.total || 0;

      document.getElementById('hdr-total').textContent = total;
      document.getElementById('hdr-updated').textContent = new Date().toLocaleTimeString();
      document.getElementById('s-total').textContent = total;
      document.getElementById('ft-total').textContent = total;

      const remediated = incidents.filter(i => i.status === 'remediated').length;
      const dryrun     = incidents.filter(i => (i.action_taken||'').startsWith('dry_run')).length;
      const errors     = incidents.filter(i => i.status === 'error').length;
      document.getElementById('s-remediated').textContent = remediated;
      document.getElementById('s-dryrun').textContent     = dryrun;
      document.getElementById('s-errors').textContent     = errors;

      renderFeed(incidents);

      const content = document.getElementById('content');
      if (!incidents.length) {
        content.innerHTML = `<div class="empty"><pre>${esc(ROBOT)}</pre><p>No incidents detected — cluster is healthy 🟢</p></div>`;
        return;
      }

      const rows = incidents.map((inc, i) => `
        <tr class="data-row" id="row-${i}" onclick="toggle(${i})">
          <td><i class="chev">&#9654;</i>${esc(fmtTs(inc.timestamp))}</td>
          <td>${alertBadge(inc.alert)}</td>
          <td><span class="pod-name">${esc(inc.pod||'—')}</span></td>
          <td>${esc(inc.namespace||'—')}</td>
          <td>${statusBadge(inc.status, inc.action_taken)}</td>
          <td>${confBar(inc.rca)}</td>
          <td style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(inc.action_taken||'—')}</td>
        </tr>
        <tr class="rca-row" id="rca-${i}">
          <td class="rca-cell" colspan="7">${rcaHtml(inc.rca)}</td>
        </tr>`).join('');

      content.innerHTML = `<div class="table-wrap"><table>
        <thead><tr>
          <th>Timestamp</th>
          <th>Alert</th>
          <th>Pod</th>
          <th>Namespace</th>
          <th>Status</th>
          <th>Confidence</th>
          <th>Action</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table></div>`;
    }

    function toggle(i) {
      document.getElementById('rca-'+i).classList.toggle('open');
      document.getElementById('row-'+i).classList.toggle('expanded');
    }

    // ── data fetches ─────────────────────────────────────────────────────
    function loadRoot() {
      fetch('/api/info')
        .then(r => r.json())
        .then(d => {
          const p = d.llm_provider || '—';
          document.getElementById('hb-llm').textContent = d.llm_model || p;
          document.getElementById('hb-ns').textContent  = d.namespace || '—';
          document.getElementById('ft-llm').textContent = p.charAt(0).toUpperCase() + p.slice(1);
          const dryEl = document.getElementById('hb-dry');
          dryEl.innerHTML = d.dry_run
            ? '<span class="hb-dot hb-warn"></span> Enabled'
            : '<span class="hb-dot hb-online"></span> Disabled';
        })
        .catch(() => {});
    }

    function loadHealth() {
      fetch('/health')
        .then(r => r.json())
        .then(d => {
          const el = document.getElementById('hb-k8s');
          el.innerHTML = d.kubernetes === 'ok'
            ? '<span class="hb-dot hb-online"></span> Connected'
            : '<span class="hb-dot hb-err"></span> Unreachable';
        })
        .catch(() => { document.getElementById('hb-k8s').textContent = '⚠ Unknown'; });
    }

    function load() {
      fetch('/incidents')
        .then(r => r.json())
        .then(render)
        .catch(() => { document.getElementById('hdr-updated').textContent = 'fetch failed'; });
      resetBar();
    }

    function resetBar() {
      const b = document.getElementById('rbar');
      b.style.animation = 'none';
      void b.offsetWidth;
      b.style.animation = '';
    }

    load();
    loadRoot();
    loadHealth();
    setInterval(load, 30000);
    setInterval(loadRoot, 30000);
    setInterval(loadHealth, 60000);
  </script>
</body>
</html>"""
