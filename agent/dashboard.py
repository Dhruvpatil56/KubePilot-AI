def get_dashboard_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>KubePilot AI</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background: #0d1117;
      color: #c9d1d9;
      font-family: 'Courier New', Courier, monospace;
      font-size: 14px;
      min-height: 100vh;
    }

    /* ── refresh progress bar ── */
    #refresh-bar {
      height: 2px;
      background: #58a6ff;
      width: 100%;
      transform-origin: left;
      animation: shrink 30s linear infinite;
    }
    @keyframes shrink { from { transform: scaleX(1); } to { transform: scaleX(0); } }

    /* ── header ── */
    header {
      background: #161b22;
      border-bottom: 1px solid #30363d;
      padding: 14px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .logo { color: #58a6ff; font-size: 18px; letter-spacing: 1px; font-weight: bold; }
    .header-meta { color: #8b949e; font-size: 12px; text-align: right; line-height: 1.6; }
    .header-meta span { color: #c9d1d9; }

    /* ── main ── */
    main { padding: 24px; max-width: 1400px; margin: 0 auto; }

    /* ── stat cards ── */
    .stats {
      display: flex;
      gap: 14px;
      margin-bottom: 22px;
      flex-wrap: wrap;
    }
    .stat-card {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 6px;
      padding: 12px 20px;
      min-width: 130px;
    }
    .stat-label { color: #8b949e; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
    .stat-value { color: #58a6ff; font-size: 26px; font-weight: bold; margin-top: 4px; }

    /* ── table ── */
    .table-wrap {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 6px;
      overflow: hidden;
    }
    table { width: 100%; border-collapse: collapse; }
    thead { background: #21262d; }
    th {
      padding: 10px 14px;
      text-align: left;
      color: #8b949e;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1px;
      border-bottom: 1px solid #30363d;
      white-space: nowrap;
    }
    tbody tr.data-row {
      border-bottom: 1px solid #21262d;
      cursor: pointer;
      transition: background 0.12s;
    }
    tbody tr.data-row:last-of-type { border-bottom: none; }
    tbody tr.data-row:hover { background: #1c2128; }
    td { padding: 10px 14px; vertical-align: middle; }

    /* ── badge ── */
    .badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: bold;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      white-space: nowrap;
    }
    .badge-red    { background: #3d1d1d; color: #f85149; border: 1px solid #6e2020; }
    .badge-yellow { background: #2d2a1a; color: #e3b341; border: 1px solid #5a4a1a; }
    .badge-green  { background: #1a2d1a; color: #3fb950; border: 1px solid #1a4a1a; }
    .badge-blue   { background: #1a1f2d; color: #58a6ff; border: 1px solid #1a2a4a; }
    .badge-gray   { background: #21262d; color: #8b949e; border: 1px solid #30363d; }

    /* ── RCA expand row ── */
    tr.rca-row { display: none; }
    tr.rca-row.open { display: table-row; }
    .rca-cell { padding: 0 14px 12px 14px !important; }
    .rca-box {
      background: #0d1117;
      border: 1px solid #30363d;
      border-radius: 4px;
      padding: 14px 18px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px 24px;
    }
    .rca-field { display: flex; flex-direction: column; gap: 3px; }
    .rca-field.full { grid-column: 1 / -1; }
    .rca-key {
      color: #8b949e;
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 1px;
    }
    .rca-val { color: #c9d1d9; line-height: 1.5; }

    /* ── empty / loading ── */
    .empty-state {
      text-align: center;
      padding: 64px 24px;
      color: #8b949e;
    }
    .empty-state .icon { font-size: 44px; margin-bottom: 12px; }
    .empty-state p { font-size: 15px; }
  </style>
</head>
<body>
  <div id="refresh-bar"></div>

  <header>
    <div class="logo">&#9096; KubePilot AI</div>
    <div class="header-meta">
      <div>Incidents: <span id="hdr-total">—</span></div>
      <div>Updated: <span id="hdr-updated">—</span></div>
    </div>
  </header>

  <main>
    <div class="stats">
      <div class="stat-card">
        <div class="stat-label">Total</div>
        <div class="stat-value" id="s-total">—</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Remediated</div>
        <div class="stat-value" id="s-remediated" style="color:#3fb950">—</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Dry Run</div>
        <div class="stat-value" id="s-dryrun" style="color:#58a6ff">—</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Errors</div>
        <div class="stat-value" id="s-errors" style="color:#f85149">—</div>
      </div>
    </div>

    <div id="content">
      <div class="empty-state"><div class="icon">&#8987;</div><p>Loading incidents&hellip;</p></div>
    </div>
  </main>

  <script>
    // ── helpers ────────────────────────────────────────────────────
    function escHtml(s) {
      return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }

    function fmtTs(ts) {
      if (!ts) return '—';
      try { return new Date(ts.endsWith('Z') ? ts : ts + 'Z').toLocaleString(); }
      catch(_) { return ts; }
    }

    function alertBadge(alert) {
      const a = (alert || '').toLowerCase();
      let cls = 'badge-gray';
      if (a.includes('crash') || a.includes('oom') || a.includes('critical')) cls = 'badge-red';
      else if (a.includes('notready') || a.includes('warning') || a.includes('slow')) cls = 'badge-yellow';
      return `<span class="badge ${cls}">${escHtml(alert || '—')}</span>`;
    }

    function statusBadge(status, action) {
      const act = action || '';
      if (act.startsWith('dry_run')) return '<span class="badge badge-blue">dry run</span>';
      if (status === 'remediated')   return '<span class="badge badge-green">remediated</span>';
      if (status === 'error')        return '<span class="badge badge-red">error</span>';
      if (status === 'analyzed')     return '<span class="badge badge-yellow">analyzed</span>';
      if (status === 'investigating') return '<span class="badge badge-gray">investigating</span>';
      return `<span class="badge badge-gray">${escHtml(status)}</span>`;
    }

    function confidenceHtml(rca) {
      if (!rca || rca.confidence == null) return '—';
      const pct = Math.round(rca.confidence * 100);
      const col = pct >= 70 ? '#3fb950' : pct >= 40 ? '#e3b341' : '#f85149';
      return `<span style="color:${col};font-weight:bold">${pct}%</span>`;
    }

    // ── RCA panel ──────────────────────────────────────────────────
    function rcaHtml(rca) {
      if (!rca) return '<em style="color:#8b949e">No RCA data</em>';
      const field = (key, val, full) => val != null
        ? `<div class="rca-field${full ? ' full' : ''}">
             <div class="rca-key">${key}</div>
             <div class="rca-val">${escHtml(val)}</div>
           </div>`
        : '';
      return `<div class="rca-box">
        ${field('Root Cause',          rca.root_cause,          true)}
        ${field('Reasoning',           rca.reasoning,           true)}
        ${field('Recommended Action',  rca.recommended_action,  false)}
        ${field('Risk Level',          rca.risk_level,          false)}
        ${field('Confidence',          rca.confidence != null ? Math.round(rca.confidence * 100) + '%' : null, false)}
      </div>`;
    }

    // ── render ─────────────────────────────────────────────────────
    function render(data) {
      const incidents = data.incidents || [];
      const total     = data.total || 0;

      document.getElementById('hdr-total').textContent   = total;
      document.getElementById('hdr-updated').textContent = new Date().toLocaleTimeString();
      document.getElementById('s-total').textContent     = total;

      const remediated = incidents.filter(i => i.status === 'remediated').length;
      const dryrun     = incidents.filter(i => (i.action_taken || '').startsWith('dry_run')).length;
      const errors     = incidents.filter(i => i.status === 'error').length;
      document.getElementById('s-remediated').textContent = remediated;
      document.getElementById('s-dryrun').textContent     = dryrun;
      document.getElementById('s-errors').textContent     = errors;

      const content = document.getElementById('content');

      if (incidents.length === 0) {
        content.innerHTML =
          '<div class="empty-state"><div class="icon">&#10003;</div><p>No incidents yet &mdash; the cluster looks healthy.</p></div>';
        return;
      }

      const rows = incidents.map((inc, i) => `
        <tr class="data-row" onclick="toggle(${i})">
          <td>${escHtml(fmtTs(inc.timestamp))}</td>
          <td>${alertBadge(inc.alert)}</td>
          <td>${escHtml(inc.pod || '—')}</td>
          <td>${escHtml(inc.namespace || '—')}</td>
          <td>${statusBadge(inc.status, inc.action_taken)}</td>
          <td>${confidenceHtml(inc.rca)}</td>
          <td>${escHtml(inc.action_taken || '—')}</td>
        </tr>
        <tr class="rca-row" id="rca-${i}">
          <td class="rca-cell" colspan="7">${rcaHtml(inc.rca)}</td>
        </tr>`).join('');

      content.innerHTML = `
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Alert</th>
                <th>Pod</th>
                <th>Namespace</th>
                <th>Status</th>
                <th>Confidence</th>
                <th>Action Taken</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>`;
    }

    function toggle(i) {
      document.getElementById('rca-' + i).classList.toggle('open');
    }

    // ── auto-refresh ───────────────────────────────────────────────
    function load() {
      fetch('/incidents')
        .then(r => r.json())
        .then(render)
        .catch(() => {
          document.getElementById('hdr-updated').textContent = 'fetch failed';
        });
      resetBar();
    }

    function resetBar() {
      const bar = document.getElementById('refresh-bar');
      bar.style.animation = 'none';
      void bar.offsetWidth;
      bar.style.animation = '';
    }

    load();
    setInterval(load, 30000);
  </script>
</body>
</html>"""
