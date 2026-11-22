(() => {
  const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
  const els = {
    todayLabel: document.getElementById("todayLabel"),
    updatedLabel: document.getElementById("updatedLabel"),
    statusBar: document.getElementById("statusBar"),
    warnings: document.getElementById("warnings"),
    dayTabs: document.getElementById("dayTabs"),
    timetableList: document.getElementById("timetableList"),
    assignmentsList: document.getElementById("assignmentsList"),
    emailsList: document.getElementById("emailsList"),
    assignmentFilter: document.getElementById("assignmentFilter"),
    statClasses: document.getElementById("statClasses"),
    statDueSoon: document.getElementById("statDueSoon"),
    statOverdue: document.getElementById("statOverdue"),
    statEmails: document.getElementById("statEmails"),
    refreshBtn: document.getElementById("refreshBtn"),
    importBtn: document.getElementById("importBtn"),
    modal: document.getElementById("modal"),
    importArea: document.getElementById("importArea"),
    importMsg: document.getElementById("importMsg"),
    saveImportBtn: document.getElementById("saveImportBtn"),
    saveSettingsBtn: document.getElementById("saveSettingsBtn"),
    settingsMsg: document.getElementById("settingsMsg"),
    gmailAccounts: document.getElementById("gmailAccounts"),
  };

  let data = { emails: [], timetable: [], assignments: [], connectors: [], warnings: [] };
  let selectedDay = todayName();

  function todayName() { return DAYS[(new Date().getDay() + 6) % 7]; }
  function esc(s) { return String(s ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function parseDate(v) { if (!v) return null; const d = new Date(v); return isNaN(d) ? null : d; }
  function fmtTime(d) { return d ? d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : ''; }
  function fmtDateTime(v) {
    const d = parseDate(v); if (!d) return '';
    const now = new Date(); const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const that = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    const diff = Math.round((that - today) / 86400000);
    const t = fmtTime(d);
    if (diff === 0) return `Today ${t}`;
    if (diff === 1) return `Tomorrow ${t}`;
    if (diff === -1) return `Yesterday ${t}`;
    return d.toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short' }) + (t ? ` ${t}` : '');
  }
  function fmtAgo(v) {
    const d = parseDate(v); if (!d) return '';
    const mins = Math.round((Date.now() - d) / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.round(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.round(hrs / 24);
    return `${days}d ago`;
  }
  function colorFor(text) {
    const palette = ["#6ea8ff","#8b7cff","#42c98b","#ffbf69","#ff7d7d","#4dd0e1","#f06292","#aed581"];
    let h=0; const s=String(text||'x'); for(let i=0;i<s.length;i++) h=((h<<5)-h+s.charCodeAt(i))|0; return palette[Math.abs(h)%palette.length];
  }
  function itemDay(it) {
    if (it.meta && it.meta.day) {
      const m = String(it.meta.day).toLowerCase();
      const found = DAYS.find(d => d.toLowerCase().startsWith(m) || d.toLowerCase() === m);
      if (found) return found;
    }
    const d = parseDate(it.timestamp) || parseDate(it.due);
    return d ? DAYS[(d.getDay()+6)%7] : null;
  }
  function dueInfo(v, status) {
    const d = parseDate(v); if (!d) return { label: 'No due date', kind: 'none', ms: Infinity, overdue: false, soon: false };
    const st = String(status||'').toLowerCase();
    const done = ['done','submitted','complete','completed'].includes(st);
    const ms = d - Date.now();
    const today = new Date(); today.setHours(0,0,0,0);
    const that = new Date(d); that.setHours(0,0,0,0);
    const dayDiff = Math.round((that - today)/86400000);
    if (ms < 0 && !done) return { label: dayDiff === 0 ? 'Overdue today' : `Overdue (${Math.abs(dayDiff)}d)`, kind: 'overdue', ms, overdue: true, soon: false };
    if (dayDiff === 0) return { label: `Due today ${fmtTime(d)}`, kind: 'soon', ms, overdue: false, soon: !done };
    if (dayDiff === 1) return { label: 'Due tomorrow', kind: 'soon', ms, overdue: false, soon: !done };
    if (dayDiff <= 7) return { label: `Due in ${dayDiff} days`, kind: 'soonish', ms, overdue: false, soon: !done };
    return { label: `Due ${d.toLocaleDateString([], {weekday:'short', day:'numeric', month:'short'})}`, kind: 'later', ms, overdue: false, soon: false };
  }

  function renderHeader() {
    const now = new Date();
    els.todayLabel.textContent = now.toLocaleDateString(undefined, { weekday:'long', day:'numeric', month:'long', year:'numeric' });
    const gen = parseDate(data.generated_at);
    els.updatedLabel.textContent = gen ? `Updated ${fmtAgo(data.generated_at)} (${gen.toLocaleTimeString([], {hour:'numeric', minute:'2-digit'})})` : '';
  }

  function renderStatus() {
    const cs = data.connectors || [];
    els.statusBar.innerHTML = cs.map(c => `<span class="chip"><span class="dot ${esc(c.status)}"></span><strong>${esc(c.name)}</strong><small>${esc(c.detail || c.status)}</small></span>`).join('') || '<span class="muted small">No connectors loaded.</span>';
    const ws = data.warnings || [];
    els.warnings.innerHTML = ws.map(w => `<div class="warn">${esc(w)}</div>`).join('');
  }

  function renderDayTabs() {
    const today = todayName();
    const present = new Set((data.timetable||[]).map(itemDay).filter(Boolean));
    const days = [...DAYS.filter(d => present.has(d) || d === today), ...[...present].filter(d => !DAYS.includes(d))];
    const uniq = days.filter((d,i)=>days.indexOf(d)===i);
    if (!uniq.includes(selectedDay)) selectedDay = uniq.includes(today) ? today : (uniq[0] || today);
    els.dayTabs.innerHTML = uniq.map(d => `<button class="day-tab ${d===selectedDay?'active':''} ${d===today?'today':''}" data-day="${esc(d)}">${esc(d.slice(0,3))}</button>`).join('');
    els.dayTabs.querySelectorAll('[data-day]').forEach(b => b.onclick = () => { selectedDay = b.dataset.day; renderTimetable(); renderStats(); });
  }

  function renderTimetable() {
    const items = (data.timetable||[]).filter(it => itemDay(it) === selectedDay).sort((a,b) => {
      const ta = parseDate(a.timestamp), tb = parseDate(b.timestamp);
      return (ta?ta:0) - (tb?tb:0) || String(a.title).localeCompare(String(b.title));
    });
    if (!items.length) { els.timetableList.innerHTML = `<div class="empty">No timetable items for ${esc(selectedDay)}. Import SEQTA data or configure automation in .env.</div>`; return; }
    els.timetableList.innerHTML = items.map(it => {
      const st = parseDate(it.timestamp), en = parseDate(it.due);
      const range = st && en ? `${fmtTime(st)} – ${fmtTime(en)}` : (st ? fmtTime(st) : (it.meta && it.meta.time ? String(it.meta.time) : '—'));
      const metaParts = [it.subtitle, it.meta && it.meta.room && !String(it.subtitle||'').includes(it.meta.room) ? it.meta.room : null].filter(Boolean);
      const period = it.meta && it.meta.period ? `<span class="class-tag">${esc(it.meta.period)}</span>` : '';
      const color = (it.meta && (it.meta.color || it.meta.colour)) || colorFor(it.title);
      return `<div class="class-card" style="border-left-color:${esc(color)}"><div class="class-time"><strong>${esc(range)}</strong></div><div class="class-main"><div class="subject">${esc(it.title)}</div><div class="meta">${esc(metaParts.join(' · '))}</div></div>${period}</div>`;
    }).join('');
  }

  function renderAssignments() {
    const filter = els.assignmentFilter.value;
    let items = (data.assignments||[]).map(a => ({...a, info: dueInfo(a.due || a.timestamp, a.meta && a.meta.status)}));
    if (filter === 'overdue') items = items.filter(a => a.info.overdue);
    if (filter === 'upcoming') items = items.filter(a => !a.info.overdue || a.info.kind === 'soon');
    items.sort((a,b)=>a.info.ms-b.info.ms);
    if (!items.length) { els.assignmentsList.innerHTML = `<div class="empty">No assignments to show. Import SEQTA assessments or configure automation.</div>`; return; }
    els.assignmentsList.innerHTML = items.map(a => {
      const badges = [];
      if (a.subtitle) badges.push(`<span class="badge subject">${esc(a.subtitle)}</span>`);
      if (a.info.overdue) badges.push(`<span class="badge overdue">${esc(a.info.label)}</span>`);
      else if (a.info.soon) badges.push(`<span class="badge soon">${esc(a.info.label)}</span>`);
      else badges.push(`<span class="badge">${esc(a.info.label)}</span>`);
      const notes = [a.meta && a.meta.notes, a.meta && a.meta.status && !a.info.overdue ? a.meta.status : null].filter(Boolean).join(' · ');
      return `<div class="card"><div class="card-top"><div><div class="card-title">${esc(a.title)}</div>${notes?`<div class="card-sub">${esc(notes)}</div>`:''}</div><div class="badges">${badges.join('')}</div></div></div>`;
    }).join('');
  }

  function renderEmails() {
    const items = data.emails || [];
    if (!items.length) { els.emailsList.innerHTML = `<div class="empty">No emails to show. Configure Gmail IMAP in <code>.env</code> (App Password, no Google Cloud) and restart.</div>`; return; }
    els.emailsList.innerHTML = items.map(m => {
      const when = fmtAgo(m.timestamp) || fmtDateTime(m.timestamp);
      const sub = [m.subtitle, m.meta && m.meta.snippet].filter(Boolean).join(' — ');
      return `<div class="card"><div class="card-top"><div><div class="card-title">${esc(m.title)}</div><div class="card-sub">${esc(sub)}</div></div><div class="badges">${when?`<span class="badge">${esc(when)}</span>`:''}${m.source?`<span class="badge subject">${esc(m.source)}</span>`:''}</div></div></div>`;
    }).join('');
  }

  function renderStats() {
    const today = todayName();
    const classesToday = (data.timetable||[]).filter(it => itemDay(it) === today).length;
    let dueSoon=0, overdue=0;
    (data.assignments||[]).forEach(a => { const i = dueInfo(a.due || a.timestamp, a.meta && a.meta.status); if (i.overdue) overdue++; else if (i.soon) dueSoon++; });
    els.statClasses.textContent = classesToday;
    els.statDueSoon.textContent = dueSoon;
    els.statOverdue.textContent = overdue;
    els.statEmails.textContent = (data.emails||[]).length;
  }

  function renderAll() { renderHeader(); renderStatus(); renderDayTabs(); renderTimetable(); renderAssignments(); renderEmails(); renderStats(); }

  async function load(refresh=false) {
    els.refreshBtn.disabled = true;
    try {
      const res = await fetch(`/api/dashboard${refresh?'?refresh=true':''}`, { cache: 'no-store' });
      if (res.status === 401) { location.href = '/login'; return; }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      data = await res.json();
      renderAll();
    } catch (e) {
      els.warnings.innerHTML = `<div class="warn">Could not load dashboard: ${esc(e.message)}. Is the server running?</div>`;
    } finally {
      els.refreshBtn.disabled = false;
    }
  }

  function renderGmailSettings(accounts) {
    const slots = [0,1,2].map(i => accounts && accounts[i] ? accounts[i] : {user:'', has_app_password:false, app_password_masked:''});
    els.gmailAccounts.innerHTML = slots.map((a, i) => `
      <div class="account-card">
        <div class="account-card-head">
          <div class="account-title">Account ${i+1}</div>
          <button type="button" class="btn ghost small danger" data-remove-account="${i}">Remove</button>
        </div>
        <label class="field-label" for="gmail-user-${i}">Email address</label>
        <input id="gmail-user-${i}" class="text-input" type="email" autocomplete="off" placeholder="you@gmail.com" value="${esc(a.user||'')}" />
        <label class="field-label" for="gmail-pass-${i}">App Password ${a.has_app_password ? `<span class="muted small">(saved ${esc(a.app_password_masked||'')}; leave blank to keep)</span>` : ''}</label>
        <input id="gmail-pass-${i}" class="text-input" type="password" autocomplete="off" placeholder="${a.has_app_password ? 'Leave blank to keep saved password' : '16-character app password'}" />
      </div>
    `).join('');
    els.gmailAccounts.querySelectorAll('[data-remove-account]').forEach(btn => {
      btn.addEventListener('click', () => {
        const i = btn.getAttribute('data-remove-account');
        const u = document.getElementById(`gmail-user-${i}`);
        const p = document.getElementById(`gmail-pass-${i}`);
        if (u) u.value = '';
        if (p) { p.value = ''; p.placeholder = '16-character app password'; }
        const label = btn.closest('.account-card')?.querySelector(`label[for="gmail-pass-${i}"]`);
        if (label) label.innerHTML = 'App Password';
        els.settingsMsg.textContent = `Account ${Number(i)+1} cleared — click "Save Gmail settings" to apply.`; 
        els.settingsMsg.className = 'msg';
      });
    });
  }

  async function loadSettings() {
    els.settingsMsg.textContent = 'Loading settings…'; els.settingsMsg.className = 'msg';
    try {
      const res = await fetch('/api/settings', { cache: 'no-store' });
      if (res.status === 401) { location.href = '/login'; return; }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const s = await res.json();
      renderGmailSettings(s.gmail_accounts || []);
      els.settingsMsg.textContent = ''; els.settingsMsg.className = 'msg';
    } catch (e) {
      renderGmailSettings([]);
      els.settingsMsg.textContent = `Could not load settings: ${e.message}`; els.settingsMsg.className = 'msg error';
    }
  }

  async function saveSettings() {
    const accounts = [0,1,2].map(i => {
      const user = (document.getElementById(`gmail-user-${i}`).value || '').trim();
      const app_password = (document.getElementById(`gmail-pass-${i}`).value || '').trim();
      return { user, app_password, keep_existing_password: !app_password && !!user };
    });
    els.saveSettingsBtn.disabled = true;
    els.settingsMsg.textContent = 'Saving…'; els.settingsMsg.className = 'msg';
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gmail_accounts: accounts, demo_mode: true }),
      });
      if (res.status === 401) { location.href = '/login'; return; }
      const out = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(out.detail || `HTTP ${res.status}`);
      els.settingsMsg.textContent = 'Saved. Refreshing dashboard…'; els.settingsMsg.className = 'msg';
      await load(true);
      await loadSettings();
      els.settingsMsg.textContent = 'Gmail settings saved.';
    } catch (e) {
      els.settingsMsg.textContent = `Save failed: ${e.message}`; els.settingsMsg.className = 'msg error';
    } finally {
      els.saveSettingsBtn.disabled = false;
    }
  }

  function openModal(show) {
    els.modal.classList.toggle('hidden', !show);
    els.modal.setAttribute('aria-hidden', show?'false':'true');
    if (show) {
      els.importMsg.textContent=''; els.importMsg.className='msg';
      els.settingsMsg.textContent=''; els.settingsMsg.className='msg';
      loadSettings();
    }
  }

  async function saveImport() {
    const text = els.importArea.value.trim();
    if (!text) { els.importMsg.textContent = 'Paste SEQTA JSON first.'; els.importMsg.className='msg error'; return; }
    try {
      const payload = JSON.parse(text);
      els.saveImportBtn.disabled = true;
      const res = await fetch('/api/seqta/import', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      if (res.status === 401) { location.href = '/login'; return; }
      const out = await res.json().catch(()=>({}));
      if (!res.ok) throw new Error(out.detail || `HTTP ${res.status}`);
      els.importMsg.textContent = 'Imported and saved. Refreshing…'; els.importMsg.className='msg';
      await load(true);
      els.importMsg.textContent = 'SEQTA data imported successfully.';
    } catch (e) {
      els.importMsg.textContent = `Import failed: ${e.message}`; els.importMsg.className='msg error';
    } finally { els.saveImportBtn.disabled = false; }
  }

  els.refreshBtn.onclick = () => load(true);
  els.importBtn.onclick = () => openModal(true);
  els.assignmentFilter.onchange = () => { renderAssignments(); };
  els.saveImportBtn.onclick = saveImport;
  els.saveSettingsBtn.onclick = saveSettings;
  els.modal.addEventListener('click', e => { if (e.target && e.target.dataset && e.target.dataset.close) openModal(false); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') openModal(false); });

  renderHeader();
  load(false);
  setInterval(() => load(false), 60000);
})();
