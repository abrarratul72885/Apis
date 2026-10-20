/* APIS core: tiny helpers shared by every screen. No frameworks, no build step. */
(function () {
  'use strict';
  var A = window.A = { S: { profile: {}, settings: {}, enums: {}, today: '' }, views: {} };
  var NS = 'http://www.w3.org/2000/svg';

  var P = {
    home: '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
    work: '<path d="M9 11l3 3 8-8"/><path d="M20 12v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h9"/>',
    map: '<path d="M12 21s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/>',
    pipe: '<rect x="3" y="4" width="5" height="16" rx="1.5"/><rect x="10" y="4" width="5" height="10" rx="1.5"/><rect x="17" y="4" width="4" height="13" rx="1.5"/>',
    chart: '<path d="M4 20V10"/><path d="M10 20V4"/><path d="M16 20v-7"/><path d="M22 20H2"/>',
    report: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h6"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    trash: '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/>',
    x: '<path d="M6 6l12 12M18 6L6 18"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    link: '<path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/>',
    image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="M21 16l-5-5-8 8"/>',
    download: '<path d="M12 4v11"/><path d="M7 11l5 5 5-5"/><path d="M4 20h16"/>',
    upload: '<path d="M12 16V5"/><path d="M7 9l5-5 5 5"/><path d="M4 20h16"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5"/>',
    moon: '<path d="M20 14a8 8 0 1 1-10-10 6.5 6.5 0 0 0 10 10z"/>',
    pin: '<path d="M12 17v5"/><path d="M8 3h8l-1 7 3 3v2H6v-2l3-3z"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    alert: '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.01"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.01"/>',
    award: '<circle cx="12" cy="9" r="6"/><path d="M8.5 14L7 22l5-3 5 3-1.5-8"/>',
    grad: '<path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c0 1.5 3 3 6 3s6-1.5 6-3v-5"/>',
    brief: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/><path d="M3 13h18"/>',
    chev: '<path d="M9 6l6 6-6 6"/>',
    back: '<path d="M15 6l-6 6 6 6"/>',
    file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
    print: '<path d="M7 9V3h10v6"/><rect x="4" y="9" width="16" height="8" rx="2"/><path d="M7 14h10v7H7z"/>',
    folder: '<path d="M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    spark: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>',
    refresh: '<path d="M20 11a8 8 0 0 0-14-4L4 9"/><path d="M4 4v5h5"/><path d="M4 13a8 8 0 0 0 14 4l2-2"/><path d="M20 20v-5h-5"/>',
    check: '<path d="M5 12l5 5 9-10"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    ext: '<path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    archive: '<rect x="3" y="4" width="18" height="4" rx="1"/><path d="M5 8v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8M10 12h4"/>',
    sheet: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M4 9h16M4 15h16M10 3v18"/>',
    cal: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    phone: '<rect x="7" y="2" width="10" height="20" rx="2.5"/><path d="M11 18h2"/>',
    more: '<circle cx="5" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="19" cy="12" r="1.2"/>'
  };
  A.icon = function (n, cls) {
    var s = document.createElementNS(NS, 'svg');
    s.setAttribute('viewBox', '0 0 24 24');
    s.setAttribute('class', 'ic ' + (cls || ''));
    s.setAttribute('aria-hidden', 'true');
    s.innerHTML = P[n] || '';
    return s;
  };

  /* ---------- element builder ---------- */
  function add(el, k) {
    if (k == null || k === false) return;
    if (Array.isArray(k)) { k.forEach(function (x) { add(el, x); }); return; }
    el.appendChild(k.nodeType ? k : document.createTextNode(String(k)));
  }
  var h = A.h = function (tag, attrs) {
    var el = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v == null || v === false) return;
      if (k === 'class') el.className = v;
      else if (k.slice(0, 2) === 'on' && typeof v === 'function') el.addEventListener(k.slice(2), v);
      else if (k === 'value') el.value = v;
      else if (k === 'checked') el.checked = !!v;
      else if (v === true) el.setAttribute(k, '');
      else el.setAttribute(k, v);
    });
    for (var i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  };
  A.$ = function (sel, root) { return (root || document).querySelector(sel); };
  A.clear = function (el) { while (el.firstChild) el.removeChild(el.firstChild); return el; };
  A.mount = function (el, kids) { A.clear(el); add(el, kids); return el; };

  /* ---------- formatting ---------- */
  var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  var DAY = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  A.pd = function (s) { var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || ''); return m ? new Date(+m[1], +m[2] - 1, +m[3]) : null; };
  A.iso = function (d) { return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2); };
  A.addDays = function (s, n) { var d = A.pd(s); d.setDate(d.getDate() + n); return A.iso(d); };
  A.date = function (s, withYear) { var d = A.pd(s); return d ? DAY[d.getDay()] + ', ' + d.getDate() + ' ' + MON[d.getMonth()] + (withYear ? ' ' + d.getFullYear() : '') : (s || ''); };
  A.shortDate = function (s) { var d = A.pd(s); return d ? d.getDate() + ' ' + MON[d.getMonth()] + ' ' + d.getFullYear() : (s || ''); };
  A.month = function (s) { var m = /^(\d{4})-(\d{2})/.exec(s || ''); return m ? MON[+m[2] - 1] + ' ' + m[1] : ''; };
  A.span = function (a, b) { return a ? A.month(a) + ' - ' + (b ? A.month(b) : 'Present') : (b ? A.month(b) : ''); };
  A.lakh = function (n) {
    n = Math.round(Number(n) || 0);
    var neg = n < 0; var s = String(Math.abs(n));
    if (s.length > 3) { var t = s.slice(-3), r = s.slice(0, -3); s = r.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + t; }
    return (neg ? '-' : '') + s;
  };
  A.money = function (n, plain) { var c = (A.S.settings && A.S.settings.currency) || '৳'; return n == null || n === '' ? '-' : (n < 0 ? '-' : '') + (plain ? '' : c) + A.lakh(Math.abs(n)); };
  A.pct = function (v) { return v == null ? 'n/a' : (Math.round(v * 10) / 10) + '%'; };
  A.greet = function () { var hr = new Date().getHours(); return hr < 5 ? 'Good night' : hr < 12 ? 'Good morning' : hr < 17 ? 'Good afternoon' : 'Good evening'; };
  A.plural = function (n, w) { return n + ' ' + w + (n === 1 ? '' : 's'); };
  A.url = function (u) { u = (u || '').trim(); return !u ? '' : /^https?:\/\//i.test(u) ? u : 'https://' + u; };
  A.file = function (n) { return n ? '/files/' + n : ''; };
  A.initials = function (n) { return (n || 'A').split(/\s+/).slice(0, 2).map(function (w) { return w[0]; }).join('').toUpperCase(); };

  /* wording changes with the workspace chosen in Settings */
  var WORDS = {
    sales: { route: 'Route', routes: 'Routes', territory: 'Territory', client: 'Client', clients: 'Clients', salesName: 'Sales and Territory', pipeName: 'Projects and Pipeline' },
    banking: { route: 'Branch or unit', routes: 'Branches and units', territory: 'Region', client: 'Application', clients: 'Applications', salesName: 'Branch Performance', pipeName: 'Applications and Pipeline' },
    general: { route: 'Area', routes: 'Areas', territory: 'Group', client: 'Item', clients: 'Items', salesName: 'Targets and Results', pipeName: 'Projects and Pipeline' }
  };
  A.W = function (k) { var w = WORDS[(A.S.settings && A.S.settings.workspace) || 'sales'] || WORDS.sales; return w[k] || k; };

  /* ---------- network ---------- */
  A.api = function (method, url, body, extra) {
    var o = { method: method, headers: {}, credentials: 'same-origin' };
    if (method !== 'GET') o.headers['X-APIS'] = '1';
    if (extra && extra.headers) Object.keys(extra.headers).forEach(function (k) { o.headers[k] = extra.headers[k]; });
    if (body !== undefined) {
      if (body instanceof Blob || body instanceof ArrayBuffer) o.body = body;
      else { o.headers['Content-Type'] = 'application/json'; o.body = JSON.stringify(body); }
    }
    return fetch(url, o).catch(function () {
      throw new Error('APIS cannot be reached. Check that it is still running on your laptop.');
    }).then(function (r) {
      if (extra && extra.blob && r.ok) return r.blob().then(function (b) { return { blob: b, name: (/filename="([^"]+)"/.exec(r.headers.get('Content-Disposition') || '') || [])[1] || 'download' }; });
      return r.json().catch(function () { return null; }).then(function (d) {
        if (r.status === 401 && url.indexOf('/api/auth/') !== 0) { if (A.onLoggedOut) A.onLoggedOut(); }
        if (!r.ok) { var e = new Error((d && d.error) || 'Something went wrong'); e.status = r.status; e.data = d; throw e; }
        return d;
      });
    });
  };
  A.get = function (u) { return A.api('GET', u); };
  A.post = function (u, b) { return A.api('POST', u, b === undefined ? {} : b); };
  A.put = function (u, b) { return A.api('PUT', u, b); };
  A.del = function (u) { return A.api('DELETE', u); };
  A.save = function (blobRes) {
    var a = h('a', { href: URL.createObjectURL(blobRes.blob), download: blobRes.name });
    document.body.appendChild(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
  };
  A.download = function (url, body) {
    return A.api(body ? 'POST' : 'GET', url, body, { blob: true }).then(A.save);
  };

  /* ---------- feedback ---------- */
  var toastEl, toastT;
  A.toast = function (msg, bad) {
    if (toastEl) toastEl.remove();
    toastEl = h('div', { class: 'toast' + (bad ? ' bad' : ''), role: 'status' }, msg);
    document.body.appendChild(toastEl);
    clearTimeout(toastT); toastT = setTimeout(function () { toastEl && toastEl.remove(); }, bad ? 6000 : 2800);
  };
  A.fail = function (e) { A.toast(e && e.message ? e.message : 'Something went wrong', true); };
  A.busy = function (btn, fn) {
    btn.setAttribute('disabled', '');
    return Promise.resolve().then(fn).then(function (r) { btn.removeAttribute('disabled'); return r; }, function (e) { btn.removeAttribute('disabled'); throw e; });
  };

  /* ---------- sheets ---------- */
  A.sheet = function (opts) {
    var prevFocus = document.activeElement;
    var scrim = h('div', { class: 'scrim', onclick: function (e) { if (e.target === scrim) close(); } });
    var close = function () { scrim.remove(); document.removeEventListener('keydown', key); if (prevFocus && prevFocus.focus) try { prevFocus.focus(); } catch (e) { } if (opts.onClose) opts.onClose(); };
    var key = function (e) { if (e.key === 'Escape') close(); };
    document.addEventListener('keydown', key);
    var foot = opts.actions && opts.actions.length ? h('div', { class: 'foot' }, opts.actions.map(function (a) {
      return h('button', { class: 'btn ' + (a.cls || ''), type: 'button', onclick: function (e) { a.onclick(e.currentTarget, api); } }, a.label);
    })) : null;
    var sheet = h('div', { class: 'sheet', role: 'dialog', 'aria-modal': 'true', 'aria-label': opts.title },
      h('div', { class: 'bar' }, h('h3', null, opts.title), h('button', { class: 'icon-btn', type: 'button', 'aria-label': 'Close', onclick: close }, A.icon('x', 'sm'))),
      h('div', { class: 'body' }, opts.body), foot);
    scrim.appendChild(sheet);
    document.body.appendChild(scrim);
    var first = sheet.querySelector('input:not([type=hidden]),textarea,select');
    if (first && !opts.noFocus && window.matchMedia('(pointer:fine)').matches) first.focus();
    var api = { close: close, el: sheet };
    return api;
  };
  A.confirm = function (title, text, okLabel, danger) {
    return new Promise(function (res) {
      var done = false;
      var s = A.sheet({
        title: title, body: h('p', { class: 'mute' }, text), onClose: function () { if (!done) res(false); },
        actions: [{ label: 'Cancel', cls: 'gray', onclick: function () { s.close(); } },
        { label: okLabel || 'Yes', cls: danger ? 'danger' : '', onclick: function () { done = true; res(true); s.close(); } }]
      });
    });
  };

  /* ---------- pictures: shrink big phone photos before saving ---------- */
  A.shrink = function (file, max) {
    max = max || 1800;
    if (!/^image\/(jpeg|png|webp)$/.test(file.type) || file.size < 350000) return Promise.resolve(file);
    return new Promise(function (res) {
      var img = new Image(); var url = URL.createObjectURL(file);
      img.onload = function () {
        var k = Math.min(1, max / Math.max(img.width, img.height));
        var c = document.createElement('canvas'); c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
        c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
        URL.revokeObjectURL(url);
        c.toBlob(function (b) { res(b && b.size < file.size ? b : file); }, file.type === 'image/png' ? 'image/png' : 'image/jpeg', 0.86);
      };
      img.onerror = function () { URL.revokeObjectURL(url); res(file); };
      img.src = url;
    });
  };
  A.upload = function (file) {
    return A.shrink(file).then(function (b) { return A.api('POST', '/api/upload', b, { headers: { 'Content-Type': b.type || 'application/octet-stream' } }); });
  };
  A.pick = function (accept, multiple) {
    return new Promise(function (res) {
      var i = h('input', { type: 'file', accept: accept, multiple: !!multiple, class: 'hide' });
      i.addEventListener('change', function () { res(Array.prototype.slice.call(i.files)); i.remove(); });
      document.body.appendChild(i); i.click();
    });
  };

  /* ---------- forms ---------- */
  /* field: {k, label, type: text|area|select|date|month|number|time|email|url|check|photo|photos|docs, opts, req, half, help, ph} */
  A.form = function (fields, values) {
    values = values || {};
    var inputs = {}, err = h('div', { class: 'formerr hide', role: 'alert' });
    var root = h('div', { class: 'form' });
    fields.forEach(function (f) {
      var v = values[f.k]; var el, wrap = h('div', { class: 'f' + (f.half ? ' half' : '') });
      var id = 'f_' + f.k + Math.random().toString(36).slice(2, 6);
      var label = h('label', { class: 'l', for: id }, f.label + (f.req ? ' *' : ''));
      if (f.type === 'area') { el = h('textarea', { id: id, placeholder: f.ph || '', rows: f.rows || 4 }); el.value = v || ''; }
      else if (f.type === 'select') {
        el = h('select', { id: id }, (f.opts || []).map(function (o) { var ov = typeof o === 'object' ? o.v : o, ol = typeof o === 'object' ? o.l : o; return h('option', { value: ov }, ol); }));
        el.value = v != null && v !== '' ? v : (f.def != null ? f.def : (f.opts && (typeof f.opts[0] === 'object' ? f.opts[0].v : f.opts[0])));
      } else if (f.type === 'check') {
        el = h('input', { type: 'checkbox', id: id, checked: v == null ? !!f.def : !!v });
        wrap.appendChild(h('label', { class: 'switch', for: id }, h('span', null, f.label), el));
        inputs[f.k] = { get: function () { return el.checked; }, f: f }; root.appendChild(wrap);
        if (f.help) wrap.appendChild(h('div', { class: 'help' }, f.help));
        return;
      } else if (f.type === 'photo' || f.type === 'photos' || f.type === 'docs') {
        var list = f.type === 'photo' ? (v ? [v] : []) : (v || []).slice();
        var tiles = h('div', { class: 'tiles-p' }); var holder = h('div', { class: 'photo-field' }, tiles);
        var draw = function () {
          A.clear(tiles);
          list.forEach(function (n, i) {
            var isPdf = /\.pdf$/.test(n);
            tiles.appendChild(h('div', { class: 'pt' }, isPdf ? h('div', { class: 'faint', style: 'display:grid;place-items:center;height:100%;font-weight:700' }, 'PDF') : h('img', { src: A.file(n), alt: '' }),
              h('button', { type: 'button', 'aria-label': 'Remove', onclick: function () { list.splice(i, 1); draw(); } }, A.icon('x'))));
          });
          if (f.type !== 'photo' || !list.length) tiles.appendChild(h('button', {
            type: 'button', class: 'add', 'aria-label': 'Add', onclick: function (e) {
              var b = e.currentTarget;
              A.pick(f.type === 'docs' ? 'application/pdf,image/*' : 'image/*', f.type !== 'photo').then(function (files) {
                if (!files.length) return; holder.classList.add('busy');
                return files.slice(0, 12 - list.length).reduce(function (p, file) { return p.then(function () { return A.upload(file).then(function (r) { if (f.type === 'photo') list = [r.file]; else list.push(r.file); draw(); }); }); }, Promise.resolve());
              }).catch(A.fail).then(function () { holder.classList.remove('busy'); });
            }
          }, A.icon('plus')));
        };
        draw(); el = holder;
        inputs[f.k] = { get: function () { return f.type === 'photo' ? (list[0] || '') : list.slice(); }, f: f };
        wrap.appendChild(label); wrap.appendChild(holder);
        if (f.help) wrap.appendChild(h('div', { class: 'help' }, f.help));
        root.appendChild(wrap); return;
      } else {
        el = h('input', { id: id, type: f.type || 'text', placeholder: f.ph || '', inputmode: f.type === 'number' ? 'decimal' : null, autocomplete: 'off', autocapitalize: f.type === 'email' || f.type === 'url' ? 'off' : null });
        if (f.type === 'number') el.setAttribute('step', 'any');
        el.value = v == null ? '' : v;
        if (f.list && f.list.length) {
          var dl = h('datalist', { id: id + '_l' }, f.list.map(function (o) { return h('option', { value: o }); }));
          el.setAttribute('list', id + '_l'); wrap.appendChild(dl);
        }
      }
      inputs[f.k] = { get: function () { return el.value; }, f: f, el: el };
      wrap.appendChild(label); wrap.appendChild(el);
      if (f.help) wrap.appendChild(h('div', { class: 'help' }, f.help));
      root.appendChild(wrap);
    });
    root.appendChild(err);
    return {
      el: root, inputs: inputs,
      get: function () { var o = {}; Object.keys(inputs).forEach(function (k) { o[k] = inputs[k].get(); }); return o; },
      error: function (m) { err.textContent = m || ''; err.classList.toggle('hide', !m); if (m) err.scrollIntoView({ block: 'nearest' }); }
    };
  };
  /* one call that opens a sheet with a form and saves it */
  A.editor = function (o) {
    var form = A.form(o.fields, o.values);
    var s = A.sheet({
      title: o.title, body: form.el, actions: (o.onDelete ? [{
        label: 'Delete', cls: 'danger', onclick: function (btn) {
          A.confirm('Delete this?', o.deleteText || 'This cannot be undone.', 'Delete', true).then(function (y) {
            if (y) A.busy(btn, function () { return o.onDelete(); }).then(function () { s.close(); if (o.done) o.done(); }, A.fail);
          });
        }
      }] : []).concat([{ label: 'Cancel', cls: 'gray', onclick: function () { s.close(); } }, {
        label: o.saveLabel || 'Save', onclick: function (btn) {
          form.error('');
          A.busy(btn, function () { return o.onSave(form.get()); }).then(function (r) { s.close(); if (o.toast !== false) A.toast(o.toast || 'Saved'); if (o.done) o.done(r); }, function (e) { form.error(e.message); });
        }
      }])
    });
    return s;
  };

  /* ---------- small reusable pieces ---------- */
  A.pageHead = function (title, lead, actions) {
    return h('div', { class: 'pagehead' }, h('div', null, h('h1', { class: 'title' }, title), lead ? h('p', { class: 'lead' }, lead) : null), actions ? h('div', { class: 'acts' }, actions) : null);
  };
  A.empty = function (title, text, btn) {
    return h('div', { class: 'empty' }, h('img', { src: '/assets/logo.png', alt: '' }), h('b', null, title), h('div', null, text), btn || null);
  };
  A.seg = function (items, value, onChange) {
    var root = h('div', { class: 'seg', role: 'tablist' });
    items.forEach(function (it) {
      var k = typeof it === 'object' ? it.k : it, l = typeof it === 'object' ? it.l : it;
      root.appendChild(h('button', {
        type: 'button', role: 'tab', 'data-k': k, class: k === value ? 'on' : '', 'aria-selected': k === value ? 'true' : 'false', onclick: function () {
          Array.prototype.forEach.call(root.children, function (c) { var on = c.getAttribute('data-k') === k; c.classList.toggle('on', on); c.setAttribute('aria-selected', on); });
          onChange(k);
        }
      }, l));
    });
    return root;
  };
  A.pill = function (text, kind) { return h('span', { class: 'pill ' + (kind || '') }, text); };
  A.loading = function (t) { return h('div', { class: 'loading' }, t || 'Loading...'); };
  A.debounce = function (fn, ms) { var t; return function () { var a = arguments, s = this; clearTimeout(t); t = setTimeout(function () { fn.apply(s, a); }, ms || 250); }; };
  A.lightbox = function (list, i) {
    var cur = i;
    var img = h('img', { src: A.file(list[cur]), alt: '' });
    var box = h('div', { class: 'lightbox', onclick: function (e) { if (e.target === box) box.remove(); } }, img,
      h('button', { class: 'icon-btn x', 'aria-label': 'Close', onclick: function () { box.remove(); } }, A.icon('x')),
      list.length > 1 ? h('button', { class: 'icon-btn pv', 'aria-label': 'Previous', onclick: function () { cur = (cur + list.length - 1) % list.length; img.src = A.file(list[cur]); } }, A.icon('back')) : null,
      list.length > 1 ? h('button', { class: 'icon-btn nx', 'aria-label': 'Next', onclick: function () { cur = (cur + 1) % list.length; img.src = A.file(list[cur]); } }, A.icon('chev')) : null);
    var k = function (e) { if (e.key === 'Escape') { box.remove(); document.removeEventListener('keydown', k); } };
    document.addEventListener('keydown', k); document.body.appendChild(box);
  };
  A.applyTheme = function (t) {
    var r = document.documentElement;
    if (t === 'light' || t === 'dark') r.setAttribute('data-theme', t); else r.removeAttribute('data-theme');
    try { if (t === 'light' || t === 'dark') localStorage.setItem('apis_theme', t); else localStorage.removeItem('apis_theme'); } catch (e) { }
    var m = document.querySelector('meta[name=theme-color]'); if (m) m.content = (t === 'dark' || (t !== 'light' && window.matchMedia('(prefers-color-scheme: dark)').matches)) ? '#000000' : '#0a57cc';
  };
  /* simple bar chart rows */
  A.bars = function (rows, o) {
    o = o || {};
    return h('div', { class: 'bars' }, rows.map(function (r) {
      var pct = r.pct == null ? 0 : Math.min(100, r.pct);
      return h('div', { class: 'bar-item' },
        h('div', { class: 'lab' }, h('b', null, r.label), h('span', { class: 'mute small num' }, r.note || '')),
        h('div', { class: 'track', role: 'img', 'aria-label': r.label + ' ' + A.pct(r.pct) }, h('div', { class: 'fill ' + (r.tone || ''), style: 'width:' + pct + '%' })));
    }));
  };
  /* small line/column chart as SVG; points: [{x,y}] */
  A.columns = function (pts, o) {
    o = o || {};
    var W = 560, H = 190, pl = 8, pr = 8, pt = 14, pb = 28;
    var max = Math.max.apply(null, pts.map(function (p) { return Math.max(p.y || 0, p.t || 0); }).concat([1]));
    var bw = (W - pl - pr) / Math.max(pts.length, 1);
    var svg = document.createElementNS(NS, 'svg'); svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H); svg.setAttribute('class', 'spark'); svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', o.label || 'Chart');
    var g = '';
    pts.forEach(function (p, i) {
      var hh = ((p.y || 0) / max) * (H - pt - pb), x = pl + i * bw + bw * 0.18, w = bw * 0.64;
      g += '<rect x="' + x + '" y="' + (H - pb - hh) + '" width="' + w + '" height="' + Math.max(hh, 1) + '" rx="5" fill="var(--blue)"><title>' + (p.x + ': ' + A.lakh(p.y)).replace(/[<&]/g, '') + '</title></rect>';
      if (p.t) { var ty = H - pb - (p.t / max) * (H - pt - pb); g += '<line x1="' + (x - 3) + '" x2="' + (x + w + 3) + '" y1="' + ty + '" y2="' + ty + '" stroke="var(--ink)" stroke-width="2" opacity=".55"/>'; }
      if (pts.length <= 14 || i % Math.ceil(pts.length / 10) === 0) g += '<text x="' + (x + w / 2) + '" y="' + (H - 8) + '" text-anchor="middle">' + String(p.x).replace(/[<&]/g, '') + '</text>';
    });
    g += '<line x1="' + pl + '" x2="' + (W - pr) + '" y1="' + (H - pb) + '" y2="' + (H - pb) + '" stroke="var(--line)"/>';
    svg.innerHTML = g; return svg;
  };
  A.copy = function (text) {
    return (navigator.clipboard && navigator.clipboard.writeText ? navigator.clipboard.writeText(text) : Promise.reject()).then(function () { A.toast('Copied'); }, function () {
      var t = h('textarea', { style: 'position:fixed;opacity:0' }); t.value = text; document.body.appendChild(t); t.select(); try { document.execCommand('copy'); A.toast('Copied'); } catch (e) { A.toast('Press Ctrl+C to copy', true); } t.remove();
    });
  };
})();
