/* Business Analysis: upload many Excel/CSV files, map columns, compare, read the report */
(function () {
  var h = A.h;
  var S = { files: [], use: {}, maps: {}, mode: 'performance', group: 'territory', period: 'month', from: '', to: '', dedupe: true, keys: [], cmp: [] };
  var GROUPS = [['territory', 'Territory'], ['route', 'Route'], ['distributor', 'Distributor'], ['salesperson', 'Salesperson'], ['outlet', 'Outlet'], ['product', 'Product'], ['category', 'Category'], ['', 'No grouping']];
  var FORMULAS = [['Achievement %', 'Actual sales / Target sales x 100'], ['Sales gap', 'Actual sales - Target sales'], ['Absolute growth', 'Current period sales - Previous period sales'],
  ['Growth rate %', '(Current - Previous) / Previous x 100. Shown as "not calculable" when Previous is zero.'], ['Contribution %', 'Group sales / Total sales x 100'],
  ['Totals and growth', 'Always calculated from combined totals, never by averaging percentages.'], ['Missing values', 'Left out of totals, never treated as zero. Missing columns are explained, not guessed.'],
  ['Duplicates', 'Rows identical in every mapped column are left out (you can switch this off).']];
  var result = null, out = h('div'), filesBox = h('div'), mapBox = h('div'), optBox = h('div');

  var key = function (f, s) { return f + '::' + s; };
  var loadFiles = function () { return A.get('/api/bi/files').then(function (fs) { S.files = fs; fs.forEach(function (f) { f.sheets.forEach(function (s) { if (S.use[key(f.id, s.name)] === undefined) S.use[key(f.id, s.name)] = f.sheets.length === 1; }); }); drawFiles(); drawMaps(); }, A.fail); };

  function upload(files) {
    var list = Array.prototype.slice.call(files);
    if (!list.length) return;
    A.toast('Uploading ' + A.plural(list.length, 'file') + '...');
    list.reduce(function (p, f) {
      return p.then(function () { return A.api('POST', '/api/bi/upload', f, { headers: { 'X-Filename': encodeURIComponent(f.name), 'Content-Type': 'application/octet-stream' } }).then(null, function (e) { A.toast(f.name + ': ' + e.message, true); }); });
    }, Promise.resolve()).then(loadFiles).then(function () { A.toast('Files added'); });
  }

  function drawFiles() {
    var drop = h('div', { class: 'card', style: 'text-align:center;border:2px dashed var(--line);background:none', ondragover: function (e) { e.preventDefault(); }, ondrop: function (e) { e.preventDefault(); upload(e.dataTransfer.files); } },
      h('div', { class: 'mute', style: 'margin-bottom:10px' }, 'Drop Excel (.xlsx) or CSV files here, up to 20 at a time. Your originals are never changed.'),
      h('button', { class: 'btn', onclick: function () { A.pick('.xlsx,.xlsm,.csv', true).then(upload); } }, A.icon('upload', 'sm'), 'Choose files'));
    A.mount(filesBox, [drop, S.files.length ? h('div', { class: 'group', style: 'margin-top:12px' }, S.files.map(function (f) {
      return h('div', { class: 'org-block' }, h('div', { style: 'display:flex;align-items:center;gap:10px' }, h('div', { class: 'lead-ic' }, A.icon('sheet')), h('div', { class: 'grow', style: 'flex:1;min-width:0' }, h('div', { class: 't', style: 'font-weight:650;overflow-wrap:anywhere' }, f.name), h('div', { class: 's small mute' }, f.added + ' · ' + Math.round(f.size / 1024) + ' KB')),
        h('button', { class: 'icon-btn', 'aria-label': 'Remove ' + f.name, onclick: function () { A.confirm('Remove this file?', 'Only the copy inside APIS is removed. Your original stays where it is.', 'Remove', true).then(function (y) { if (y) A.del('/api/bi/files/' + f.id).then(loadFiles, A.fail); }); } }, A.icon('trash', 'sm'))),
        h('div', { class: 'chips', style: 'margin-top:8px' }, f.sheets.map(function (s) {
          var k = key(f.id, s.name);
          return h('button', { class: 'chip' + (S.use[k] ? ' on' : ''), 'aria-pressed': !!S.use[k], onclick: function (e) { S.use[k] = !S.use[k]; e.currentTarget.classList.toggle('on', S.use[k]); drawMaps(); } }, (S.use[k] ? '✓ ' : '') + s.name + ' (' + s.rows + ' rows)');
        })));
    })) : null]);
  }

  function selected() { var r = []; S.files.forEach(function (f) { f.sheets.forEach(function (s) { if (S.use[key(f.id, s.name)]) r.push({ f: f, s: s.name, k: key(f.id, s.name) }); }); }); return r; }

  function drawMaps() {
    var sel = selected();
    if (!sel.length) { A.mount(mapBox, h('div', { class: 'group' }, A.empty('Choose worksheets', 'Add files above, then tap the worksheets you want to include.'))); A.mount(optBox, ''); return; }
    A.mount(mapBox, sel.map(function (x) {
      var box = h('div', { class: 'card' }, A.loading('Reading ' + x.s + '...')); loadMap(x, box); return box;
    }));
    drawOpts();
  }
  function loadMap(x, box) {
    var m = S.maps[x.k];
    var go = function (header) {
      return A.get('/api/bi/files/' + x.f.id + '/preview?sheet=' + encodeURIComponent(x.s) + (header != null ? '&header=' + header : '')).then(function (p) {
        var cur = S.maps[x.k] = { file: x.f.id, sheet: x.s, header_row: p.header_row, columns: p.columns.map(function (c) { return c.name; }), map: (m && header == null && m.map) || p.suggest, preview: p };
        renderMap(x, box, cur);
      }, function (e) { A.mount(box, h('div', { class: 'banner bad' }, e.message)); });
    };
    if (m && m.preview) renderMap(x, box, m); else go();
    box._reload = go;
  }
  function renderMap(x, box, cur) {
    var p = cur.preview;
    var hdr = h('input', { class: 'in', type: 'number', min: 1, value: cur.header_row + 1, style: 'width:90px', 'aria-label': 'Header row', onchange: function (e) { var v = Math.max(1, +e.target.value || 1) - 1; delete cur.map; S.maps[x.k] = Object.assign({}, cur, { map: null, preview: null }); loadMapNew(x, box, v); } });
    var sels = p.fields.map(function (fl) {
      var s = h('select', { class: 'in', 'aria-label': fl.label + ' column', onchange: function (e) { if (e.target.value) cur.map[fl.key] = e.target.value; else delete cur.map[fl.key]; drawOpts(); } },
        [h('option', { value: '' }, '- not in this file -')].concat(cur.columns.map(function (c) { return h('option', { value: c, selected: cur.map[fl.key] === c }, c); })));
      return h('div', { class: 'f half', style: 'display:flex;flex-direction:column;gap:4px;min-width:0' }, h('label', { class: 'l', style: 'font-size:13px;font-weight:600;color:var(--mute)' }, fl.label), s);
    });
    A.mount(box, [h('div', { style: 'display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:6px' }, h('div', null, h('div', { class: 'h3' }, x.f.name), h('div', { class: 'small mute' }, 'Worksheet "' + x.s + '" · ' + A.lakh(p.row_count) + ' rows')),
      h('label', { class: 'small mute', style: 'display:flex;gap:8px;align-items:center' }, 'Headings are on row', hdr)),
    h('div', { style: 'overflow-x:auto;margin:8px 0' }, h('table', { style: 'border-collapse:collapse;font-size:13px;min-width:100%' },
      h('thead', null, h('tr', null, p.columns.map(function (c) { return h('th', { style: 'text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);white-space:nowrap' }, c.name, h('div', { class: 'faint', style: 'font-weight:400' }, c.type + (c.missing ? ', ' + c.missing + ' blank' : ''))); }))),
      h('tbody', null, p.sample.slice(0, 4).map(function (r) { return h('tr', null, r.map(function (v) { return h('td', { style: 'padding:5px 10px;border-bottom:1px solid var(--line2);white-space:nowrap;max-width:200px;overflow:hidden;text-overflow:ellipsis' }, String(v)); })); })))),
    h('div', { class: 'mute small', style: 'margin:10px 4px 6px' }, 'Tell APIS what each column is. Different names in different files are fine.'), h('div', { class: 'form' }, sels)]);
  }
  function loadMapNew(x, box, header) { A.mount(box, A.loading()); A.get('/api/bi/files/' + x.f.id + '/preview?sheet=' + encodeURIComponent(x.s) + '&header=' + header).then(function (p) { var cur = S.maps[x.k] = { file: x.f.id, sheet: x.s, header_row: p.header_row, columns: p.columns.map(function (c) { return c.name; }), map: p.suggest, preview: p }; renderMap(x, box, cur); drawOpts(); }, A.fail); }

  function drawOpts() {
    var sel = selected().map(function (x) { return S.maps[x.k]; }).filter(Boolean);
    var perf = S.mode === 'performance';
    var body = [];
    if (perf) {
      body.push(h('div', { class: 'form' },
        h('div', { class: 'f half' }, h('label', { class: 'l' }, 'Compare by'), h('select', { class: 'in', onchange: function (e) { S.group = e.target.value; } }, GROUPS.map(function (g) { return h('option', { value: g[0], selected: g[0] === S.group }, g[1]); }))),
        h('div', { class: 'f half' }, h('label', { class: 'l' }, 'Time unit'), h('select', { class: 'in', onchange: function (e) { S.period = e.target.value; } }, [['month', 'Month'], ['week', 'Week'], ['quarter', 'Quarter'], ['day', 'Day']].map(function (g) { return h('option', { value: g[0], selected: g[0] === S.period }, g[1]); }))),
        h('div', { class: 'f half' }, h('label', { class: 'l' }, 'From (optional)'), h('input', { type: 'date', class: 'in', value: S.from, onchange: function (e) { S.from = e.target.value; } })),
        h('div', { class: 'f half' }, h('label', { class: 'l' }, 'To (optional)'), h('input', { type: 'date', class: 'in', value: S.to, onchange: function (e) { S.to = e.target.value; } })),
        h('div', { class: 'f' }, h('label', { class: 'switch' }, h('span', null, 'Leave out duplicate rows'), h('input', { type: 'checkbox', checked: S.dedupe, onchange: function (e) { S.dedupe = e.target.checked; } })))));
    } else if (sel.length) {
      var first = sel[0].columns;
      var multi = function (title, arr, help) {
        return h('div', { class: 'f', style: 'margin-bottom:10px' }, h('div', { class: 'mute small', style: 'margin:0 4px 6px' }, title), h('div', { class: 'chips' }, first.map(function (c) {
          return h('button', { class: 'chip' + (arr.indexOf(c) >= 0 ? ' on' : ''), onclick: function (e) { var i = arr.indexOf(c); if (i >= 0) arr.splice(i, 1); else arr.push(c); e.currentTarget.classList.toggle('on', i < 0); } }, c);
        })), help ? h('div', { class: 'help small mute', style: 'margin-top:4px' }, help) : null);
      };
      body.push(multi('Match records using these columns (from the first worksheet)', S.keys, 'For example Route or Outlet ID. You decide what counts as the same record.'), multi('Compare the values in these columns', S.cmp, 'Optional. Leave empty to only find added and removed records.'));
    }
    var run = h('button', { class: 'btn', onclick: function (e) { A.busy(e.currentTarget, runAnalysis).catch(A.fail); } }, A.icon('chart', 'sm'), 'Analyse');
    A.mount(optBox, h('div', { class: 'card stack' }, h('h3', { class: 'h3' }, 'Options'), body, h('div', { class: 'acts' }, run,
      h('button', { class: 'btn soft', onclick: savePreset }, 'Save these settings'), h('button', { class: 'btn soft', onclick: loadPresets }, 'Use saved settings'))));
  }

  function request() {
    var sel = selected().map(function (x) { return S.maps[x.k]; }).filter(Boolean);
    if (!sel.length) throw new Error('Choose at least one worksheet.');
    var req = { mode: S.mode, dedupe: S.dedupe, group_by: S.group, period: S.period, from: S.from, to: S.to };
    if (S.mode === 'reconcile') {
      if (sel.length < 2) throw new Error('Choose at least two worksheets to compare.');
      if (!S.keys.length) throw new Error('Pick at least one column to match records on.');
      req.keys = S.keys.slice(); req.compare = S.cmp.slice();
      req.sources = sel.map(function (c, i) {
        var map = {}; S.keys.concat(S.cmp).forEach(function (k) { var same = c.columns.filter(function (x) { return x.toLowerCase() === k.toLowerCase(); })[0]; if (i === 0) map[k] = k; else if (same) map[k] = same; });
        return { file: c.file, sheet: c.sheet, header_row: c.header_row, map: c.map && i > 0 && c.recmap ? c.recmap : map };
      });
    } else req.sources = sel.map(function (c) { return { file: c.file, sheet: c.sheet, header_row: c.header_row, map: c.map }; });
    return req;
  }
  function runAnalysis() {
    var req = request(); A.mount(out, A.loading('Analysing...'));
    return A.post('/api/bi/analyze', req).then(function (r) { result = { res: r, req: req }; drawResult(); out.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, function (e) { A.mount(out, ''); throw e; });
  }
  function savePreset() {
    var f = A.form([{ k: 'name', label: 'Name', req: true, ph: 'e.g. Territory report July to September' }]);
    var s = A.sheet({ title: 'Save these settings', body: f.el, actions: [{ label: 'Cancel', cls: 'gray', onclick: function () { s.close(); } }, { label: 'Save', onclick: function () {
      var body = { mode: S.mode, group: S.group, period: S.period, dedupe: S.dedupe, keys: S.keys, cmp: S.cmp, from: S.from, to: S.to, use: S.use, maps: Object.keys(S.maps).reduce(function (o, k) { var m = S.maps[k]; o[k] = { file: m.file, sheet: m.sheet, header_row: m.header_row, map: m.map }; return o; }, {}) };
      A.post('/api/bi/presets', { name: f.get().name, body: body }).then(function () { s.close(); A.toast('Saved'); }, function (e) { f.error(e.message); });
    } }] });
  }
  function loadPresets() {
    A.get('/api/bi/presets').then(function (list) {
      var s = A.sheet({ title: 'Saved settings', body: list.length ? h('div', { class: 'group' }, list.map(function (p) {
        return h('div', { class: 'row tap', role: 'button', tabindex: '0', onclick: function () {
          var b = p.body; var ids = S.files.map(function (f) { return f.id; });
          S.mode = b.mode || 'performance'; S.group = b.group || ''; S.period = b.period || 'month'; S.dedupe = b.dedupe !== false; S.keys = b.keys || []; S.cmp = b.cmp || []; S.from = b.from || ''; S.to = b.to || '';
          Object.keys(S.use).forEach(function (k) { S.use[k] = false; });
          Object.keys(b.use || {}).forEach(function (k) { if (ids.indexOf(k.split('::')[0]) >= 0) S.use[k] = b.use[k]; });
          S.maps = {}; Object.keys(b.maps || {}).forEach(function (k) { if (ids.indexOf(b.maps[k].file) >= 0) S.maps[k] = Object.assign({ columns: null }, b.maps[k]); });
          s.close(); A.reload(); A.toast('Settings loaded. Files that were removed are skipped.');
        } }, h('div', { class: 'grow' }, h('div', { class: 't' }, p.name), h('div', { class: 's' }, p.saved)), h('button', { class: 'icon-btn', 'aria-label': 'Delete', onclick: function (e) { e.stopPropagation(); A.del('/api/bi/presets/' + p.id).then(function () { s.close(); loadPresets(); }, A.fail); } }, A.icon('trash', 'sm')));
      })) : A.empty('Nothing saved yet', 'Run an analysis and tap "Save these settings".') });
    }, A.fail);
  }

  function table(cols, rows) {
    return h('div', { style: 'overflow-x:auto' }, h('table', { style: 'border-collapse:collapse;width:100%;font-size:14px' },
      h('thead', null, h('tr', null, cols.map(function (c) { return h('th', { style: 'text-align:' + (c.num ? 'right' : 'left') + ';padding:8px 10px;border-bottom:1px solid var(--line);color:var(--mute);font-weight:600;white-space:nowrap' }, c.l); }))),
      h('tbody', null, rows.map(function (r) { return h('tr', null, cols.map(function (c) { return h('td', { class: c.num ? 'num' : '', style: 'text-align:' + (c.num ? 'right' : 'left') + ';padding:8px 10px;border-bottom:1px solid var(--line2);white-space:nowrap' }, c.f(r)); })); }))));
  }

  function drawResult() {
    var r = result.res;
    var exportBtn = h('button', { class: 'btn soft', onclick: function (e) { A.busy(e.currentTarget, function () { return A.download('/api/bi/export', result.req); }).catch(A.fail); } }, A.icon('download', 'sm'), 'Download Excel');
    var copyBtn = h('button', { class: 'btn soft', onclick: function () { A.copy(r.report); } }, 'Copy report');
    if (r.mode === 'reconcile') {
      A.mount(out, [h('div', { class: 'head', style: 'display:flex;justify-content:space-between;align-items:center;margin:24px 4px 10px' }, h('h2', { class: 'h2' }, 'Reconciliation'), h('div', { class: 'acts' }, copyBtn, exportBtn)),
        r.pairs.map(function (p) {
          return h('div', { class: 'card stack', style: 'margin-bottom:12px' }, h('div', { class: 'h3' }, p.base + '  →  ' + p.other),
            h('div', { class: 'tiles', style: 'margin:0' }, [['Match', p.matching], ['Only in second', p.added_count], ['Only in first', p.removed_count], ['Changed', p.changed_count]].map(function (t) { return h('div', { class: 'tile', style: 'min-height:84px' }, h('div', { class: 'k' }, t[0]), h('div', { class: 'v num' }, t[1])); })),
            p.changed.length ? h('div', null, h('b', null, 'Changed values'), table([{ l: 'Record', f: function (c) { return c.key; } }, { l: 'Column', f: function (c) { return c.diffs.map(function (d) { return d.column; }).join(', '); } }, { l: 'Old → New', f: function (c) { return c.diffs.map(function (d) { return d.old + ' → ' + d.new; }).join('; '); } }], p.changed.slice(0, 60))) : null,
            p.added.length ? h('div', { class: 'small' }, h('b', null, 'Only in the second file: '), p.added.slice(0, 40).join(', ')) : null, p.removed.length ? h('div', { class: 'small' }, h('b', null, 'Only in the first file: '), p.removed.slice(0, 40).join(', ')) : null);
        }),
        h('div', { class: 'banner' }, 'A record missing from one file is not proof of a business loss. Please check each one before drawing conclusions.')]);
      return;
    }
    var hd = r.headline, cur = A.S.settings.currency || '৳';
    var tile = function (k, v, d, tone) { return h('div', { class: 'tile' }, h('div', { class: 'k' }, k), h('div', { class: 'v num', style: tone ? 'color:var(--' + tone + ')' : '' }, v), d ? h('div', { class: 'd' }, d) : null); };
    var tiles = [tile('Total actual', A.money(hd.actual), A.plural(hd.records, 'record'))];
    if (hd.target != null) { tiles.push(tile('Achievement', hd.achievement_pct == null ? 'n/a' : A.pct(hd.achievement_pct), 'of ' + A.money(hd.target) + ' target'), tile('Gap to target', A.money(hd.gap), '', hd.gap < 0 ? 'bad' : 'good')); }
    if (hd.growth_pct !== undefined) tiles.push(tile('Growth', hd.growth_pct == null ? 'n/a' : A.pct(hd.growth_pct), hd.current_period + ' vs ' + hd.previous_period, hd.growth_abs < 0 ? 'bad' : 'good'));
    var cols = [{ l: '#', f: function (g) { return g.rank; }, num: true }, { l: S.group ? (GROUPS.filter(function (x) { return x[0] === S.group; })[0] || ['', ''])[1] : 'Group', f: function (g) { return g.name; } }, { l: 'Actual', f: function (g) { return A.money(g.actual, true); }, num: true }];
    if (r.groups[0].target !== undefined) cols.push({ l: 'Target', f: function (g) { return A.money(g.target, true); }, num: true }, { l: 'Achv.', f: function (g) { return A.pct(g.achievement_pct); }, num: true }, { l: 'Gap', f: function (g) { return A.money(g.gap, true); }, num: true });
    cols.push({ l: 'Share', f: function (g) { return A.pct(g.share_pct); }, num: true });
    if (r.groups[0].growth_pct !== undefined) cols.push({ l: 'Growth', f: function (g) { return g.growth_pct == null ? 'n/a' : A.pct(g.growth_pct); }, num: true });
    if (r.groups[0].stock_outs !== undefined) cols.push({ l: 'Stock-outs', f: function (g) { return g.stock_outs; }, num: true });
    A.mount(out, [
      h('div', { class: 'head', style: 'display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin:24px 4px 10px' }, h('h2', { class: 'h2' }, 'Results'), h('div', { class: 'acts' }, copyBtn, exportBtn)),
      h('div', { class: 'tiles', style: 'margin:0' }, tiles),
      r.periods.length > 1 ? h('div', { class: 'card', style: 'margin-top:12px' }, h('div', { class: 'h3', style: 'margin-bottom:6px' }, 'By ' + r.period_unit), A.columns(r.periods.map(function (p) { return { x: p.period.slice(2), y: p.actual, t: p.target }; }), { label: 'Sales by period' })) : null,
      h('div', { class: 'card', style: 'margin-top:12px' }, h('div', { class: 'h3', style: 'margin-bottom:6px' }, 'Ranking'), table(cols, r.groups.slice(0, 100))),
      r.quality.length ? h('div', { class: 'card', style: 'margin-top:12px' }, h('div', { class: 'h3', style: 'margin-bottom:6px' }, 'Data quality'), r.quality.map(function (q) { return h('div', { style: 'padding:4px 0' }, h('b', null, q.count + ' '), q.issue, q.examples ? h('div', { class: 'small mute' }, q.examples.join('; ')) : null); })) : null,
      r.missing.length ? h('div', { class: 'banner', style: 'margin-top:12px' }, r.missing.join(' ')) : null,
      h('div', { class: 'mail', style: 'margin-top:12px' }, h('div', { class: 'mh' }, h('div', { class: 't' }, 'Plain-English report')), h('pre', null, r.report))]);
  }

  A.views.analysis = function () {
    var modeSeg = A.seg([{ k: 'performance', l: 'Compare performance' }, { k: 'reconcile', l: 'Reconcile file versions' }], S.mode, function (k) { S.mode = k; drawOpts(); });
    var help = h('details', { class: 'guide' }, h('summary', null, 'How the numbers are calculated', A.icon('info', 'sm')), h('div', { class: 'stack', style: 'padding-bottom:14px' }, FORMULAS.map(function (f) { return h('div', null, h('b', null, f[0] + ': '), f[1]); })));
    loadFiles();
    return h('div', null, A.pageHead('Business Analysis', 'Upload up to 20 Excel or CSV files, map the columns, and get clear numbers and a plain-English report. Every figure comes from fixed formulas, never from guesses.'),
      h('div', { class: 'stack' }, h('div', null, h('div', { class: 'mute small', style: 'margin:0 4px 6px' }, 'What do you want to do?'), modeSeg,
        h('p', { class: 'small mute', style: 'margin:8px 4px 0' }, 'Compare performance: territories, routes, products, distributors or periods. Reconcile: find added, removed and changed records between versions of a file.')),
        h('div', null, h('h2', { class: 'h2', style: 'margin:8px 4px' }, '1. Files'), filesBox), h('div', null, h('h2', { class: 'h2', style: 'margin:8px 4px' }, '2. Match the columns'), mapBox),
        h('div', null, h('h2', { class: 'h2', style: 'margin:8px 4px' }, '3. Analyse'), optBox), help, out));
  };
})();
