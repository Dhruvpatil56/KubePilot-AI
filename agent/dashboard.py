def get_dashboard_html() -> str:
    return r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>KubePilot AI — Dashboard</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background: #0d1117;
      color: #c9d1d9;
      font-family: 'SF Mono', 'Fira Code', 'Courier New', monospace;
      font-size: 13px;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* ── refresh bar ── */
    #rbar {
      height: 2px;
      background: linear-gradient(90deg, #58a6ff, #79c0ff, #58a6ff);
      background-size: 200% 100%;
      transform-origin: left;
      animation: shrink 30s linear infinite;
      flex-shrink: 0;
    }
    @keyframes shrink { from { transform: scaleX(1); } to { transform: scaleX(0); } }

    /* ── header ── */
    header {
      background: #161b22;
      border-bottom: 1px solid #30363d;
      padding: 11px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-shrink: 0;
    }
    .logo-row { display: flex; align-items: center; gap: 10px; }
    .logo { color: #58a6ff; font-size: 17px; font-weight: bold; letter-spacing: 1px; }
    .ver-badge {
      background: #21262d; border: 1px solid #30363d;
      color: #8b949e; font-size: 10px; padding: 2px 7px; border-radius: 10px;
    }
    .live-dot {
      display: inline-flex; align-items: center; gap: 5px;
      font-size: 11px; color: #3fb950; letter-spacing: 0.5px;
    }
    .live-dot::before {
      content: ''; width: 7px; height: 7px; background: #3fb950;
      border-radius: 50%; display: inline-block;
      animation: pulse 2s ease-in-out infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(63,185,80,0.4); }
      50% { opacity: 0.5; box-shadow: 0 0 0 4px rgba(63,185,80,0); }
    }
    .hdr-right { display: flex; align-items: center; gap: 18px; font-size: 11px; color: #8b949e; }
    .hdr-right span { color: #c9d1d9; }

    /* ── health bar ── */
    #health-bar {
      background: #161b22;
      border-bottom: 1px solid #30363d;
      padding: 6px 24px;
      display: flex; gap: 6px; align-items: center; flex-wrap: wrap;
      flex-shrink: 0; font-size: 11px;
    }
    .hb-item { color: #8b949e; padding: 0 8px; }
    .hb-item span { color: #c9d1d9; }
    .hb-sep { color: #30363d; user-select: none; }

    /* ── layout ── */
    main { flex: 1; padding: 18px 24px; max-width: 1600px; width: 100%; margin: 0 auto; }
    .layout { display: flex; gap: 16px; align-items: flex-start; }
    .primary { flex: 1; min-width: 0; }
    .sidebar { width: 270px; flex-shrink: 0; }

    /* ── stat cards ── */
    .stats { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
    .stat-card {
      background: #161b22; border: 1px solid #30363d; border-radius: 6px;
      padding: 12px 16px; flex: 1; min-width: 110px;
      position: relative; overflow: hidden;
      transition: transform 0.15s, box-shadow 0.15s;
      cursor: default;
    }
    .stat-card::before {
      content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    }
    .stat-card.c-total::before  { background: linear-gradient(90deg,#58a6ff,#388bfd); }
    .stat-card.c-ok::before     { background: linear-gradient(90deg,#3fb950,#2ea043); }
    .stat-card.c-dry::before    { background: linear-gradient(90deg,#79c0ff,#58a6ff); }
    .stat-card.c-err::before    { background: linear-gradient(90deg,#f85149,#da3633); }
    .stat-card:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,0.35); }
    .stat-icon { font-size: 17px; margin-bottom: 4px; }
    .stat-label { color: #8b949e; font-size: 9px; text-transform: uppercase; letter-spacing: 1px; }
    .stat-value { font-size: 26px; font-weight: bold; margin-top: 2px; }
    .stat-card.c-total .stat-value { color: #58a6ff; }
    .stat-card.c-ok    .stat-value { color: #3fb950; }
    .stat-card.c-dry   .stat-value { color: #79c0ff; }
    .stat-card.c-err   .stat-value { color: #f85149; }

    /* ── table ── */
    .table-wrap { background: #161b22; border: 1px solid #30363d; border-radius: 6px; overflow: hidden; }
    table { width: 100%; border-collapse: collapse; }
    thead { background: #21262d; }
    th {
      padding: 9px 12px; text-align: left; color: #8b949e;
      font-size: 10px; text-transform: uppercase; letter-spacing: 1px;
      border-bottom: 1px solid #30363d; white-space: nowrap;
    }
    tbody tr.data-row {
      border-bottom: 1px solid #21262d;
      cursor: pointer;
      transition: background 0.1s, border-left-color 0.1s;
      border-left: 3px solid transparent;
    }
    tbody tr.data-row:last-of-type { border-bottom: none; }
    tbody tr.data-row:hover { background: #1c2128; border-left-color: #58a6ff; }
    tbody tr.data-row.expanded { border-left-color: #79c0ff; }
    td { padding: 9px 12px; vertical-align: middle; font-size: 12px; }
    .chev { display: inline-block; transition: transform 0.2s; color: #8b949e; margin-right: 5px; font-style: normal; font-size: 10px; }
    tr.data-row.expanded .chev { transform: rotate(90deg); color: #79c0ff; }

    /* ── badges ── */
    .badge {
      display: inline-flex; align-items: center; gap: 4px;
      padding: 2px 7px; border-radius: 10px;
      font-size: 10px; font-weight: bold; text-transform: uppercase;
      letter-spacing: 0.5px; white-space: nowrap;
    }
    .bd-red    { background:#3d1d1d; color:#f85149; border:1px solid #6e2020; }
    .bd-yellow { background:#2d2a1a; color:#e3b341; border:1px solid #5a4a1a; }
    .bd-green  { background:#1a2d1a; color:#3fb950; border:1px solid #1a4a1a; }
    .bd-blue   { background:#1a1f2d; color:#58a6ff; border:1px solid #1a2a4a; }
    .bd-gray   { background:#21262d; color:#8b949e; border:1px solid #30363d; }

    /* ── confidence bar ── */
    .cbar { display:flex; align-items:center; gap:6px; min-width:72px; }
    .cbar-bg { flex:1; height:4px; background:#21262d; border-radius:2px; overflow:hidden; }
    .cbar-fill { height:100%; border-radius:2px; }
    .cbar-pct { font-size:11px; font-weight:bold; min-width:28px; text-align:right; }

    /* ── RCA expand ── */
    tr.rca-row { display: none; }
    tr.rca-row.open { display: table-row; }
    .rca-cell { padding: 0 12px 12px 28px !important; }
    .rca-box {
      background:#0d1117; border:1px solid #30363d; border-radius:4px;
      padding:12px 16px;
      display:grid; grid-template-columns:1fr 1fr; gap:10px 20px;
      animation: slideIn 0.15s ease;
    }
    @keyframes slideIn { from { opacity:0; transform:translateY(-5px); } to { opacity:1; transform:translateY(0); } }
    .rf { display:flex; flex-direction:column; gap:3px; }
    .rf.full { grid-column: 1 / -1; }
    .rk { color:#8b949e; font-size:9px; text-transform:uppercase; letter-spacing:1px; }
    .rv { color:#c9d1d9; line-height:1.5; font-size:12px; }

    /* ── sidebar panel ── */
    .panel { background:#161b22; border:1px solid #30363d; border-radius:6px; overflow:hidden; }
    .panel-hdr {
      background:#21262d; padding:9px 14px;
      border-bottom:1px solid #30363d;
      font-size:11px; font-weight:bold; text-transform:uppercase;
      letter-spacing:1px; color:#c9d1d9;
    }
    .panel-body { padding:10px 14px; }
    .feed-item { display:flex; gap:10px; padding:8px 0; border-bottom:1px solid #21262d; }
    .feed-item:last-child { border-bottom:none; }
    .fdot { width:8px; height:8px; border-radius:50%; margin-top:4px; flex-shrink:0; }
    .fdot.red    { background:#f85149; }
    .fdot.green  { background:#3fb950; }
    .fdot.yellow { background:#e3b341; }
    .fdot.blue   { background:#58a6ff; }
    .fdot.gray   { background:#8b949e; }
    .fcontent { flex:1; min-width:0; }
    .ftime   { color:#8b949e; font-size:10px; }
    .falert  { color:#c9d1d9; font-size:11px; font-weight:bold; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .faction { color:#8b949e; font-size:10px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .feed-empty { color:#8b949e; font-size:11px; text-align:center; padding:20px 0; }

    /* ── empty state ── */
    .empty { text-align:center; padding:48px 24px; color:#8b949e; }
    .empty pre { font-size:11px; line-height:1.4; color:#30363d; margin-bottom:16px; display:inline-block; text-align:left; }
    .empty p { font-size:14px; }

    /* ── footer ── */
    footer {
      background:#161b22; border-top:1px solid #30363d;
      padding:9px 24px; display:flex; align-items:center; justify-content:space-between;
      font-size:10px; color:#8b949e; flex-shrink:0;
    }
    .fsep { color:#30363d; margin:0 7px; }
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
    <div class="hb-item">&#127922; Agent: <span>Online</span></div>
    <span class="hb-sep">|</span>
    <div class="hb-item">LLM: <span id="hb-llm">&#8212;</span></div>
    <span class="hb-sep">|</span>
    <div class="hb-item">Dry Run: <span id="hb-dry">&#8212;</span></div>
    <span class="hb-sep">|</span>
    <div class="hb-item">Namespace: <span id="hb-ns">&#8212;</span></div>
    <span class="hb-sep">|</span>
    <div class="hb-item">K8s: <span id="hb-k8s">&#8212;</span></div>
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
      const col = pct >= 70 ? '#3fb950' : pct >= 40 ? '#e3b341' : '#f85149';
      return `<div class="cbar">
        <div class="cbar-bg"><div class="cbar-fill" style="width:${pct}%;background:${col}"></div></div>
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
          <td style="font-family:monospace">${esc(inc.pod||'—')}</td>
          <td>${esc(inc.namespace||'—')}</td>
          <td>${statusBadge(inc.status, inc.action_taken)}</td>
          <td>${confBar(inc.rca)}</td>
          <td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(inc.action_taken||'—')}</td>
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
      fetch('/')
        .then(r => r.json())
        .then(d => {
          const p = d.llm_provider || '—';
          document.getElementById('hb-llm').textContent    = d.llm_model || p;
          document.getElementById('hb-dry').textContent    = d.dry_run ? '🟡 Enabled' : '🟢 Disabled';
          document.getElementById('hb-ns').textContent     = d.namespace || '—';
          document.getElementById('ft-llm').textContent    = p.charAt(0).toUpperCase() + p.slice(1);
        })
        .catch(() => {});
    }

    function loadHealth() {
      fetch('/health')
        .then(r => r.json())
        .then(d => {
          document.getElementById('hb-k8s').textContent =
            d.kubernetes === 'ok' ? '🟢 Connected' : '🔴 Unreachable';
        })
        .catch(() => { document.getElementById('hb-k8s').textContent = '⚠️ Unknown'; });
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
