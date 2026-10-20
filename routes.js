/* Sales and Territory: target against actual, by route */
(function () {
  var h = A.h;
  var state = { range: '7', territory: '' };

  A.editRoute = function (item, done, opts) {
    opts = opts || {};
    A.editor({
      title: item ? 'Edit entry' : 'New entry', values: item || { date: A.S.today, target: '', actual: '', territory: state.territory }, done: done, saveLabel: item ? 'Save' : 'Add entry',
      fields: [
        { k: 'date', label: 'Date', type: 'date', req: true, half: true },
        { k: 'territory', label: A.W('territory'), req: true, half: true, list: opts.territories, ph: 'e.g. Dhanmondi' },
        { k: 'route', label: A.W('route'), req: true, list: opts.routes, ph: 'e.g. Route 4' },
        { k: 'distributor', label: 'Distributor', list: opts.distributors, ph: 'Optional' },
        { k: 'target', label: 'Target (৳)', type: 'number', half: true, req: true },
        { k: 'actual', label: 'Actual (৳)', type: 'number', half: true, req: true },
        { k: 'stock_out', label: 'There was a stock-out', type: 'check' },
        { k: 'stock_out_items', label: 'Which items ran out?', ph: 'e.g. Vanilla cup, Choco bar' },
        { k: 'remarks', label: 'Remarks', type: 'area', rows: 3, ph: 'Optional' }],
      onSave: function (d) { return item ? A.put('/api/territory/' + item.id, d) : A.post('/api/territory', d); },
      onDelete: item ? function () { return A.del('/api/territory/' + item.id); } : null
    });
  };

  function range() {
    var t = A.S.today;
    if (state.range === '1') return [t, t];
    if (state.range === '30') return [A.addDays(t, -29), t];
    return [A.addDays(t, -6), t];
  }

  A.views.sales = function () {
    var body = h('div');
    var sw = A.seg([{ k: '1', l: 'Today' }, { k: '7', l: '7 days' }, { k: '30', l: '30 days' }], state.range, function (k) { state.range = k; load(); });
    var sel = h('select', { class: 'in', style: 'width:auto;max-width:220px', 'aria-label': 'Filter by ' + A.W('territory'), onchange: function (e) { state.territory = e.target.value; load(); } });
    var load = function () {
      var r = range();
      Promise.all([A.get('/api/territory/summary?from=' + r[0] + '&to=' + r[1] + (state.territory ? '&territory=' + encodeURIComponent(state.territory) : '')),
      A.get('/api/territory?from=' + r[0] + '&to=' + r[1] + (state.territory ? '&territory=' + encodeURIComponent(state.territory) : ''))]).then(function (res) {
        var s = res[0], rows = res[1], thr = A.S.settings.alert_threshold || 80;
        var o = s.options;
        A.mount(sel, [h('option', { value: '' }, 'All ' + A.W('territory').toLowerCase() + 's')].concat(o.territories.map(function (t) { return h('option', { value: t, selected: t === state.territory }, t); })));
        sel.value = state.territory;
        var edit = function (it) { A.editRoute(it, load, o); };
        var kids = [];
        kids.push(h('div', { class: 'tiles' },
          h('div', { class: 'tile' }, h('div', { class: 'k' }, 'Achievement'), h('div', { class: 'v num' }, s.pct == null ? 'n/a' : Math.round(s.pct) + '%'), h('div', { class: 'd' }, s.pct != null && s.pct < thr ? 'Below your ' + thr + '% alert level' : 'On track')),
          h('div', { class: 'tile' }, h('div', { class: 'k' }, 'Target'), h('div', { class: 'v num' }, A.money(s.target))),
          h('div', { class: 'tile' }, h('div', { class: 'k' }, 'Actual'), h('div', { class: 'v num' }, A.money(s.actual))),
          h('div', { class: 'tile' }, h('div', { class: 'k' }, 'Gap'), h('div', { class: 'v num', style: s.actual - s.target < 0 ? 'color:var(--bad)' : 'color:var(--good)' }, A.money(s.actual - s.target)))));
        var stock = rows.filter(function (x) { return x.stock_out; });
        if (stock.length) kids.push(h('div', { class: 'banner bad', style: 'margin-top:12px' }, 'Stock-outs in this period: ' + stock.length + (stock[0].stock_out_items ? '. Latest: ' + stock[0].stock_out_items + ' on ' + stock[0].route : '')));
        if (s.routes.length) {
          kids.push(h('div', { class: 'sect two' },
            h('div', null, h('div', { class: 'head' }, h('h2', { class: 'h2' }, A.W('routes') + ' against target')),
              h('div', { class: 'card' }, A.bars(s.routes.slice().sort(function (a, b) { return (a.pct == null ? 999 : a.pct) - (b.pct == null ? 999 : b.pct); }).map(function (r) {
                return { label: r.route + (r.territory ? ' · ' + r.territory : ''), pct: r.pct, note: A.money(r.actual) + ' of ' + A.money(r.target) + (r.pct != null ? ' (' + Math.round(r.pct) + '%)' : ''), tone: r.pct == null ? '' : r.pct < thr - 20 ? 'low' : r.pct < thr ? 'mid' : '' };
              })))),
            h('div', null, h('div', { class: 'head' }, h('h2', { class: 'h2' }, 'Day by day')),
              h('div', { class: 'card' }, A.columns(s.days.map(function (d) { return { x: d.date.slice(8), y: d.actual, t: d.target }; }), { label: 'Actual sales by day with target markers' }),
                h('div', { class: 'legend', style: 'margin-top:8px' }, h('span', null, h('i', { style: 'background:var(--blue)' }), 'Actual'), h('span', null, h('i', { style: 'background:var(--ink);opacity:.55;height:3px;vertical-align:3px' }), 'Target'))))));
        }
        kids.push(h('div', { class: 'sect' }, h('div', { class: 'head' }, h('h2', { class: 'h2' }, 'Entries'), h('span', { class: 'mute small' }, A.plural(rows.length, 'entry').replace('entrys', 'entries'))),
          rows.length ? h('div', { class: 'group' }, rows.map(function (x) {
            var p = x.target ? Math.round(x.actual / x.target * 100) : null;
            return h('div', { class: 'row tap', role: 'button', tabindex: '0', onclick: function () { edit(x); }, onkeydown: function (e) { if (e.key === 'Enter') edit(x); } },
              h('div', { class: 'lead-ic' }, A.icon('map')),
              h('div', { class: 'grow' }, h('div', { class: 't' }, x.route + ' · ' + x.territory), h('div', { class: 's' }, A.date(x.date) + (x.distributor ? ' · ' + x.distributor : '') + (x.stock_out ? ' · Stock-out: ' + (x.stock_out_items || 'yes') : ''))),
              h('div', { class: 'trail' }, h('div', { style: 'text-align:right' }, h('div', { class: 'num', style: 'font-weight:650;color:var(--ink)' }, A.money(x.actual)), h('div', { class: 's num' }, 'of ' + A.money(x.target))), p != null ? A.pill(p + '%', p >= 100 ? 'good' : p < thr ? 'bad' : 'warn') : null));
          })) : h('div', { class: 'group' }, A.empty('No entries in this period', 'Add your ' + A.W('route').toLowerCase() + ' target and actual for the day.', h('button', { class: 'btn', onclick: function () { edit(null); } }, 'Add an entry'))),
          h('p', { class: 'small mute', style: 'margin:10px 4px' }, 'Have many Excel reports instead? Use Business Analysis to compare up to 20 files at once.')));
        A.mount(body, kids);
        body._opts = o;
      }, function (e) { A.mount(body, h('div', { class: 'empty' }, e.message)); });
    };
    load();
    return h('div', null, A.pageHead(A.W('salesName'), 'Target against actual, ' + A.W('routes').toLowerCase() + ' and stock-outs.',
      h('button', { class: 'btn', onclick: function () { A.editRoute(null, load, body._opts); } }, A.icon('plus', 'sm'), 'New entry')),
      h('div', { class: 'acts', style: 'margin-bottom:16px' }, sw, sel), body);
  };
})();
