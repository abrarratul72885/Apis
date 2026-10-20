/* Home: today at a glance, plus Ask APIS */
(function () {
  var h = A.h;
  var ICON = { route: 'map', stock: 'alert', lead: 'clock', docs: 'file' };

  A.ask = function () {
    var out = h('div', { class: 'stack' });
    var q = h('input', { class: 'in', type: 'text', placeholder: 'Ask about your own records...', 'aria-label': 'Your question', style: 'flex:1' });
    var go = function (text) {
      q.value = text; A.mount(out, A.loading('Looking...'));
      A.get('/api/ask?q=' + encodeURIComponent(text)).then(function (r) {
        A.mount(out, r.answers.map(function (a) {
          return h('div', { class: 'card' }, h('h3', { class: 'h3', style: 'margin-bottom:8px' }, a.title), a.lines.map(function (l) { return h('div', { style: 'padding:3px 0' }, l); }), a.source ? h('div', { class: 'small faint', style: 'margin-top:8px' }, 'From: ' + a.source) : null);
        }));
      }, A.fail);
    };
    var chips = ['What are my top tasks today?', 'What did I complete this week?', 'Which routes are below target?', 'Any overdue follow-ups?', 'What is missing from my portfolio?'];
    A.sheet({ title: 'Ask APIS', body: h('div', { class: 'stack' },
      h('form', { class: 'acts', style: 'flex-wrap:nowrap', onsubmit: function (e) { e.preventDefault(); if (q.value.trim()) go(q.value.trim()); } }, q, h('button', { class: 'btn', type: 'submit' }, 'Ask')),
      h('div', { class: 'chips' }, chips.map(function (c) { return h('button', { class: 'chip', type: 'button', onclick: function () { go(c); } }, c); })),
      out, h('p', { class: 'small faint' }, 'Answers come from your saved records only, counted by APIS. Nothing leaves your laptop.')) });
  };

  A.views.home = function () {
    return A.get('/api/dashboard').then(function (d) {
      var p = A.S.profile, first = (p.name || '').split(' ')[0] || 'there';
      var t = d.tasks, wk = d.territory.week, td = d.territory.today;
      var line = t.total ? t.done + ' of ' + t.total + ' tasks done today.' : 'Nothing logged yet today.';
      var pending = d.alerts.filter(function (a) { return a.level === 'high'; }).length;
      var hero = h('section', { class: 'hero' },
        h('div', { class: 'copy' }, h('div', { class: 'when' }, A.date(d.date, true)), h('h1', null, A.greet() + ', ' + first + '.'),
          h('p', null, line + (pending ? ' ' + A.plural(pending, 'thing') + ' need attention.' : ' Work smarter. Make an impact.')),
          h('div', { class: 'acts' }, h('button', { class: 'btn', onclick: function () { A.editLog(null, function () { A.reload(); }); } }, A.icon('plus', 'sm'), 'Log a task'),
            h('button', { class: 'btn ghost', onclick: function () { A.go('#/reports'); } }, d.eod_sent ? 'Report sent' : 'Today\'s report'))),
        h('div', { class: 'mascot' }, h('img', { src: '/assets/mascot.jpg', alt: '' })));
      var tile = function (k, v, sub, go) { return h('button', { class: 'tile', onclick: function () { A.go(go); } }, h('div', { class: 'k' }, k), h('div', { class: 'v num' }, v), sub ? h('div', { class: 'd' }, sub) : null); };
      var tiles = h('div', { class: 'tiles' },
        tile('Tasks today', [String(t.done), h('small', null, ' / ' + t.total)], t.open + ' open overall', '#/work'),
        tile('Hours logged', String(t.hours), 'today', '#/work'),
        tile(A.W('salesName').split(' ')[0] + ' this week', wk.pct == null ? 'n/a' : Math.round(wk.pct) + '%', wk.target ? A.money(wk.actual) + ' of ' + A.money(wk.target) : 'No target set', '#/sales'),
        tile('Active ' + A.W('clients').toLowerCase(), String(d.leads.active), A.money(Object.keys(d.leads.stages).reduce(function (s, k) { return s + d.leads.stages[k].amount; }, 0)) + ' in pipeline', '#/pipeline'));
      var quick = h('div', { class: 'quick' },
        [['work', 'Add a task', function () { A.editLog(null, function () { A.reload(); }); }],
        ['map', 'Add a ' + A.W('route').toLowerCase() + ' entry', function () { A.editRoute(null, function () { A.reload(); }, {}); }],
        ['pipe', 'Add a ' + A.W('client').toLowerCase(), function () { A.editLead(null, function () { A.reload(); }); }],
        ['image', 'Write a post', function () { A.editPost(null, function () { A.go('#/portfolio'); }); }]].map(function (q) {
          return h('button', { class: 'qa', onclick: q[2] }, h('div', { class: 'lead-ic' }, A.icon(q[0])), q[1]);
        }));
      var alerts = d.alerts.length ? h('div', { class: 'group' }, d.alerts.slice(0, 7).map(function (a) {
        return h('div', { class: 'row tap alert-row', role: 'button', tabindex: '0', onclick: function () { A.go(a.go); }, onkeydown: function (e) { if (e.key === 'Enter') A.go(a.go); } },
          h('div', { class: 'lead-ic ' + a.level }, A.icon(ICON[a.kind] || 'info')), h('div', { class: 'grow' }, h('div', { class: 't' }, a.title), h('div', { class: 's' }, a.detail)), h('div', { class: 'trail' }, A.icon('chev', 'sm')));
      })) : h('div', { class: 'group' }, h('div', { class: 'row alert-row' }, h('div', { class: 'lead-ic ok' }, A.icon('check')), h('div', { class: 'grow' }, h('div', { class: 't' }, 'All clear'), h('div', { class: 's' }, 'No stock-outs, missed targets or overdue follow-ups.'))));
      return h('div', null, hero, tiles,
        h('div', { class: 'sect' }, h('div', { class: 'head' }, h('h2', { class: 'h2' }, 'Needs attention')), alerts),
        h('div', { class: 'sect' }, h('div', { class: 'head' }, h('h2', { class: 'h2' }, 'Quick add')), quick));
    });
  };
})();
