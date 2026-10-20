/* App shell and router */
(function () {
  var h = A.h;
  var NAV = function () {
    return [
      { k: 'home', l: 'Home', i: 'home' }, { k: 'portfolio', l: 'My Portfolio', i: 'user' }, { k: 'work', l: 'Work and Tasks', i: 'work' },
      { k: 'analysis', l: 'Business Analysis', i: 'chart' }, { k: 'sales', l: A.W('salesName'), i: 'map' }, { k: 'pipeline', l: A.W('pipeName'), i: 'pipe' },
      { k: 'reports', l: 'Reports and Automation', i: 'report' }, { k: 'settings', l: 'Settings and Data', i: 'gear' }];
  };
  var TABS = ['home', 'work', 'sales', 'pipeline'];
  var shell = null, current = '', token = 0;

  A.onLoggedOut = function () { shell = null; A.api('GET', '/api/auth/status').then(function (s) { A.showLogin(!s.setup); }); };

  function avatarNode() {
    var p = A.S.profile;
    return p.avatar ? h('img', { src: A.file(p.avatar), alt: '' }) : h('span', null, A.initials(p.name));
  }
  A.refreshAvatar = function () { if (shell) A.mount(shell.avatar, avatarNode()); };

  function openMenu(anchor) {
    var p = A.S.profile, dark = document.documentElement.getAttribute('data-theme') === 'dark';
    var m = h('div', { class: 'menu', role: 'menu' });
    var close = function () { m.remove(); document.removeEventListener('click', outside, true); };
    var outside = function (e) { if (!m.contains(e.target)) close(); };
    var item = function (icon, label, fn) { return h('button', { class: 'mi', role: 'menuitem', onclick: function () { close(); fn(); } }, A.icon(icon, 'sm'), label); };
    m.appendChild(h('div', { class: 'mh' }, p.avatar ? h('img', { src: A.file(p.avatar), alt: '' }) : h('span', { class: 'avatar-btn' }, A.initials(p.name)),
      h('div', null, h('div', { class: 'n' }, p.name || 'You'), h('div', { class: 'w' }, p.headline || ''))));
    m.appendChild(h('hr'));
    m.appendChild(item('user', 'My Portfolio', function () { location.hash = '#/portfolio'; }));
    m.appendChild(item('print', 'Make a portfolio PDF', function () { location.hash = '#/portfolio/build'; }));
    m.appendChild(item('gear', 'Settings and Data', function () { location.hash = '#/settings'; }));
    m.appendChild(item(dark ? 'sun' : 'moon', dark ? 'Light mode' : 'Dark mode', function () {
      var t = dark ? 'light' : 'dark'; A.applyTheme(t); A.put('/api/settings', { theme: t }).catch(function () { });
    }));
    m.appendChild(h('hr'));
    m.appendChild(item('lock', 'Lock APIS', function () { A.post('/api/auth/logout').then(function () { A.onLoggedOut(); }); }));
    document.body.appendChild(m);
    var r = anchor.getBoundingClientRect();
    m.style.top = (r.bottom + 8) + 'px'; m.style.right = Math.max(12, window.innerWidth - r.right) + 'px';
    setTimeout(function () { document.addEventListener('click', outside, true); }, 0);
  }

  function openMore() {
    var list = h('div', { class: 'group' }, ['portfolio', 'analysis', 'reports', 'settings'].map(function (k) {
      var n = NAV().filter(function (x) { return x.k === k; })[0];
      return h('button', { class: 'row tap', onclick: function () { s.close(); location.hash = '#/' + k; } }, h('div', { class: 'lead-ic' }, A.icon(n.i)), h('div', { class: 'grow t' }, n.l), h('div', { class: 'trail' }, A.icon('chev', 'sm')));
    }));
    var s = A.sheet({ title: 'More', body: list, noFocus: true });
  }

  function build() {
    var nav = NAV();
    var side = h('aside', { class: 'side' }, h('div', { class: 'brand' }, h('img', { src: '/assets/logo.png', alt: '' }), h('b', null, 'APIS')),
      h('nav', { class: 'nav', 'aria-label': 'Main' }, nav.map(function (n) { return h('a', { href: '#/' + n.k, 'data-k': n.k }, A.icon(n.i), h('span', { class: 'lbl' }, n.l)); })),
      h('div', { class: 'foot nav' }, h('button', { onclick: function () { A.ask(); } }, A.icon('spark'), h('span', { class: 'lbl' }, 'Ask APIS'))));
    var crumb = h('div', { class: 'crumb' });
    var avatar = h('button', { class: 'avatar-btn', 'aria-label': 'Profile menu', onclick: function (e) { openMenu(e.currentTarget); } }, avatarNode());
    var top = h('header', { class: 'top' }, crumb, h('div', { class: 'sp' }),
      h('button', { class: 'icon-btn', 'aria-label': 'Ask APIS', onclick: function () { A.ask(); } }, A.icon('spark')), avatar);
    var view = h('div', { class: 'wrap', id: 'view', tabindex: '-1' });
    var tabs = h('nav', { class: 'tabbar', 'aria-label': 'Main' },
      TABS.map(function (k) { var n = nav.filter(function (x) { return x.k === k; })[0]; return h('a', { href: '#/' + k, 'data-k': k }, A.icon(n.i), n.l.split(' ')[0]); }),
      h('a', { href: '#', 'data-k': 'more', onclick: function (e) { e.preventDefault(); openMore(); } }, A.icon('more'), 'More'));
    var app = h('div', { class: 'app' }, side, h('main', { class: 'main' }, top, view), tabs);
    A.mount(document.getElementById('root'), app);
    window.addEventListener('scroll', function () { top.classList.toggle('scrolled', window.scrollY > 24); }, { passive: true });
    shell = { app: app, view: view, crumb: crumb, avatar: avatar, side: side, tabs: tabs };
  }

  function route() {
    if (!shell) return;
    var parts = (location.hash.replace(/^#\/?/, '') || 'home').split('/');
    var key = parts[0];
    if (!A.views[key]) { location.hash = '#/home'; return; }
    var my = ++token; current = key;
    Array.prototype.forEach.call(shell.app.querySelectorAll('[data-k]'), function (a) { a.classList.toggle('on', a.getAttribute('data-k') === key); });
    var n = NAV().filter(function (x) { return x.k === key; })[0];
    shell.crumb.textContent = n ? n.l : '';
    document.title = (n ? n.l + ' - ' : '') + 'APIS';
    A.mount(shell.view, A.loading());
    window.scrollTo(0, 0);
    Promise.resolve().then(function () { return A.views[key](parts.slice(1)); }).then(function (node) {
      if (my !== token) return;
      A.mount(shell.view, node);
    }).catch(function (e) {
      if (my !== token) return;
      A.mount(shell.view, h('div', { class: 'empty' }, h('b', null, 'This page could not load'), h('div', null, e.message), h('button', { class: 'btn', onclick: route }, 'Try again')));
    });
  }
  A.reload = route;
  A.go = function (hash) { if (location.hash === hash) route(); else location.hash = hash; };

  A.start = function () {
    return A.get('/api/bootstrap').then(function (b) {
      A.S.version = b.version; A.S.profile = b.profile; A.S.settings = b.settings; A.S.enums = b.enums; A.S.today = b.today;
      A.applyTheme(b.settings.theme);
      build();
      if (!location.hash) location.hash = '#/home'; else route();
    });
  };
  window.addEventListener('hashchange', route);

  A.get('/api/auth/status').then(function (s) {
    if (s.authed) return A.start();
    A.showLogin(!s.setup);
  }).catch(function (e) {
    A.mount(document.getElementById('root'), h('div', { class: 'empty' }, h('b', null, 'APIS is not reachable'), h('div', null, e.message)));
  });
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(function () { });
})();
