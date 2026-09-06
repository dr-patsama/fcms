/* Shared live-board runtime: auth, SSE with polling fallback, clock, i18n. */
const Board = (() => {
  const token = sessionStorage.getItem('fcms_token') || localStorage.getItem('fcms_token') || new URLSearchParams(location.search).get('token');
  if (!token) location.href = '/login?next=' + encodeURIComponent(location.pathname);
  let lang = localStorage.getItem('fcms_lang') || 'th';
  let last = null, es = null, pollTimer = null;

  const T = (en, th) => (lang === 'th' ? th : en);
  const name = (r) => lang === 'th' && r.first_name_th ? `${r.first_name_th} ${r.last_name_th || ''}` : `${r.first_name_en || ''} ${r.last_name_en || ''}`;
  const hhmm = (v) => { if (!v) return '—'; if (typeof v === 'string' && v.includes('T')) { const d = new Date(v); return d.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', hour12: false }); } return String(v).slice(0, 5); };
  const thaiDate = (d) => d.toLocaleDateString(lang === 'th' ? 'th-TH-u-ca-buddhist' : 'en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  function setLive(state) { const el = document.getElementById('live'); el.className = 'live ' + state; el.querySelector('span').textContent = state === 'on' ? T('LIVE', 'สด') : state === 'off' ? T('Reconnecting…', 'กำลังเชื่อมต่อ…') : T('Error', 'ผิดพลาด'); }

  function connect(board, render) {
    if (es) es.close();
    es = new EventSource(`/api/v1/dashboard/${board}/stream?token=${encodeURIComponent(token)}`);
    es.addEventListener('snapshot', (e) => { last = JSON.parse(e.data); setLive('on'); render(last, T, { name, hhmm, esc }); document.getElementById('upd').textContent = T('Updated', 'อัปเดต') + ' ' + hhmm(last.generated_at); });
    es.addEventListener('heartbeat', () => setLive('on'));
    es.addEventListener('error', (e) => { if (e.data) { setLive('err'); document.getElementById('err').textContent = e.data; } });
    es.onerror = () => { setLive('off'); startPoll(board, render); };
    es.onopen = () => stopPoll();
  }
  function startPoll(board, render) { if (pollTimer) return; pollTimer = setInterval(async () => { try { const r = await fetch(`/api/v1/dashboard/${board}`, { headers: { Authorization: 'Bearer ' + token } }); if (r.status === 401) location.href = '/login?next=' + location.pathname; if (r.ok) { last = await r.json(); render(last, T, { name, hhmm, esc }); } } catch (_) { } }, 10000); }
  function stopPoll() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } }

  function clock() { const d = new Date(); document.getElementById('clock').textContent = d.toLocaleTimeString('th-TH', { hour12: false }); document.getElementById('date').textContent = thaiDate(d); }
  setInterval(clock, 1000);

  function init(board, render) {
    clock();
    document.getElementById('lang').textContent = lang === 'th' ? 'EN' : 'ไทย';
    document.getElementById('lang').onclick = () => { lang = lang === 'th' ? 'en' : 'th'; localStorage.setItem('fcms_lang', lang); document.getElementById('lang').textContent = lang === 'th' ? 'EN' : 'ไทย'; clock(); if (last) render(last, T, { name, hhmm, esc }); document.querySelectorAll('[data-en]').forEach(el => el.textContent = lang === 'th' ? el.dataset.th : el.dataset.en); };
    document.querySelectorAll('[data-en]').forEach(el => el.textContent = lang === 'th' ? el.dataset.th : el.dataset.en);
    connect(board, render);
    document.addEventListener('visibilitychange', () => { if (!document.hidden && es && es.readyState === 2) connect(board, render); });
  }
  const panel = (id, rows, html, emptyMsg) => { const el = document.getElementById(id); const n = el.parentElement.querySelector('.n'); if (n) n.textContent = rows.length; el.innerHTML = rows.length ? rows.map(html).join('') : `<div class="empty">${emptyMsg}</div>`; };
  const kpi = (id, v) => { const el = document.getElementById(id); if (el && el.textContent !== String(v)) { el.textContent = v ?? '—'; el.parentElement.classList.remove('flash'); void el.offsetWidth; el.parentElement.classList.add('flash'); } };
  return { init, panel, kpi };
})();
