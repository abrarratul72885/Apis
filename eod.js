/* Work and Tasks: the daily log, history and the career log */
(function () {
  var h = A.h;
  var STAT = { 'Completed': 'good', 'In Progress': 'blue', 'Pending': 'warn' };

  A.editLog = function (item, done, preset) {
    var E = A.S.enums, v = item || Object.assign({ date: A.S.today, category: 'Task', impact: 'Medium', status: 'Pending', hours: '' }, preset || {});
    A.editor({
      title: item ? 'Edit task' : 'New task', values: v, saveLabel: item ? 'Save' : 'Add task', done: done,
      fields: [
        { k: 'title', label: 'What did you do?', req: true, ph: 'e.g. Visited 12 outlets on Route 4' },
        { k: 'date', label: 'Date', type: 'date', req: true, half: true },
        { k: 'category', label: 'Type', type: 'select', opts: E.cats, half: true },
        { k: 'impact', label: 'Impact', type: 'select', opts: E.impact, half: true, help: 'High and Medium impact work is added to your career log once completed.' },
        { k: 'status', label: 'Status', type: 'select', opts: E.status, half: true },
        { k: 'hours', label: 'Hours spent', type: 'number', half: true, ph: '0' },
        { k: 'location', label: 'Where', half: true, ph: 'Optional' },
        { k: 'result', label: 'Result or outcome', type: 'area', rows: 3, ph: 'Optional. Numbers help: "Opened 3 new outlets, ৳45,000 sales"' },
        { k: 'description', label: 'Notes', type: 'area', rows: 3, ph: 'Optional' }],
      onSave: function (d) { return item ? A.put('/api/logs/' + item.id, d) : A.post('/api/logs', d); },
      onDelete: item ? function () { return A.del('/api/logs/' + item.id); } : null,
      deleteText: item && item.status === 'Completed' && item.impact !== 'Low' ? 'The career log keeps its permanent copy of this task even if you delete it here.' : 'This cannot be undone.'
    });
  };

  function logRow(l, refresh) {
    var done = l.status === 'Completed';
    var chk = h('button', {
      class: 'checkbtn' + (done ? ' on' : ''), 'aria-label': done ? 'Mark as not done' : 'Mark as done', title: done ? 'Completed' : 'Mark done',
      onclick: function (e) { e.stopPropagation(); A.put('/api/logs/' + l.id, { status: done ? 'Pending' : 'Completed' }).then(function () { A.toast(done ? 'Moved back to pending' : 'Marked done'); refresh(); }, A.fail); }
    }, A.icon('check'));
    return h('div', { class: 'row tap', role: 'button', tabindex: '0', onclick: function () { A.editLog(l, refresh); }, onkeydown: function (e) { if (e.key === 'Enter') A.editLog(l, refresh); } },
      chk,
      h('div', { class: 'grow' }, h('div', { class: 't', style: done ? 'text-decoration:line-through;opacity:.6' : '' }, l.title),
        h('div', { class: 's' }, [l.category, l.location, l.hours ? l.hours + ' h' : ''].filter(Boolean).join(' · ')), l.result ? h('div', { class: 's' }, l.result) : null),
      h('div', { class: 'trail' }, A.pill(l.status, STAT[l.status]), h('span', { class: 'dot ' + l.impact, title: l.impact + ' impact' })));
  }

  function dayView(day, box) {
    var all = null;
    var render = function () {
      A.get('/api/logs?from=' + A.addDays(day, -45) + '&to=' + day).then(function (logs) {
        var today = logs.filter(function (l) { return l.date === day; });
        var carry = logs.filter(function (l) { return l.date < day && l.status !== 'Completed'; });
        var doneN = today.filter(function (l) { return l.status === 'Completed'; }).length;
        var hours = today.reduce(function (s, l) { return s + (l.hours || 0); }, 0);
        var kids = [
          h('div', { class: 'tiles' },
            h('div', { class: 'tile' }, h('div', { class: 'k' }, 'Done'), h('div', { class: 'v num' }, doneN, h('small', null, ' / ' + today.length))),
            h('div', { class: 'tile' }, h('div', { class: 'k' }, 'Hours'), h('div', { class: 'v num' }, Math.round(hours * 10) / 10)),
            h('div', { class: 'tile' }, h('div', { class: 'k' }, 'High impact'), h('div', { class: 'v num' }, today.filter(function (l) { return l.impact === 'High'; }).length)),
            h('div', { class: 'tile' }, h('div', { class: 'k' }, 'Carried over'), h('div', { class: 'v num' }, carry.length)))];
        kids.push(h('div', { class: 'sect' }, h('div', { class: 'head' }, h('h2', { class: 'h2' }, day === A.S.today ? 'Today' : A.date(day, true)),
          h('button', { class: 'btn sm', onclick: function () { A.editLog(null, render, { date: day }); } }, A.icon('plus', 'sm'), 'Add task')),
          today.length ? h('div', { class: 'group' }, today.map(function (l) { return logRow(l, render); })) :
            h('div', { class: 'group' }, A.empty('Nothing logged yet', 'Add what you did today. It takes ten seconds.', h('button', { class: 'btn', onclick: function () { A.editLog(null, render, { date: day }); } }, 'Add the first task')))));
        if (carry.length) kids.push(h('div', { class: 'sect' }, h('div', { class: 'head' }, h('h2', { class: 'h2' }, 'Still open from earlier'), h('span', { class: 'mute small' }, 'Last 45 days')),
          h('div', { class: 'group' }, carry.map(function (l) { return h('div', null, logRow(l, render), null); }))));
        A.mount(box, kids);
      }).catch(function (e) { A.mount(box, h('div', { class: 'empty' }, e.message)); });
    };
    render();
  }

  function historyView(box) {
    var q = h('input', { class: 'in', type: 'search', placeholder: 'Search your work log', 'aria-label': 'Search', style: 'max-width:420px' });
    var list = h('div');
    var load = function () {
      A.get('/api/logs' + (q.value.trim() ? '?search=' + encodeURIComponent(q.value.trim()) : '')).then(function (logs) {
        if (!logs.length) { A.mount(list, h('div', { class: 'group' }, A.empty('No tasks found', 'Try a different word.'))); return; }
        var by = {}; logs.forEach(function (l) { (by[l.date] = by[l.date] || []).push(l); });
        A.mount(list, Object.keys(by).sort().reverse().slice(0, 60).map(function (d) {
          return h('div', null, h('div', { class: 'day-h' }, A.date(d, true)), h('div', { class: 'group' }, by[d].map(function (l) { return logRow(l, load); })));
        }));
      }, A.fail);
    };
    q.addEventListener('input', A.debounce(load, 250));
    A.mount(box, [q, h('div', { style: 'height:8px' }), list]); load();
  }

  function careerView(box) {
    var out = h('div');
    A.mount(box, [h('p', { class: 'mute', style: 'margin-bottom:12px' }, 'Every Completed task with Medium or High impact is copied here automatically. Entries are permanent and cannot be edited, so this record is safe to show in an appraisal or interview.'), out]);
    Promise.all([A.get('/api/appraisal'), A.get('/api/appraisal/verify')]).then(function (r) {
      var rows = r[0], v = r[1];
      A.mount(out, [
        h('div', { class: 'banner ' + (v.ok ? 'good' : 'bad'), style: 'margin-bottom:12px' }, v.ok ? (rows.length ? 'Record checked: all ' + rows.length + ' entries are intact.' : 'Nothing here yet.') : 'Warning: the record was changed outside APIS near entry ' + v.broken_at + '.'),
        rows.length ? h('div', { class: 'group' }, rows.map(function (a) {
          return h('div', { class: 'row' }, h('div', { class: 'lead-ic' }, A.icon('award')), h('div', { class: 'grow' }, h('div', { class: 't' }, a.title), h('div', { class: 's' }, A.shortDate(a.date) + (a.result ? ' · ' + a.result : ''))), h('div', { class: 'trail' }, A.pill(a.impact, a.impact === 'High' ? 'bad' : 'warn')));
        })) : h('div', { class: 'group' }, A.empty('No entries yet', 'Complete a Medium or High impact task and it appears here.')),
        rows.length ? h('div', { class: 'acts', style: 'margin-top:12px' }, h('button', { class: 'btn soft', onclick: function () { A.download('/api/export.xlsx?scope=all'); } }, A.icon('download', 'sm'), 'Download everything as Excel')) : null]);
    }, A.fail);
  }

  A.views.work = function () {
    var day = A.S.today, tab = 'day';
    var box = h('div');
    var bar = h('div', { class: 'acts', style: 'margin-bottom:16px' });
    var drawBar = function () {
      var kids = [A.seg([{ k: 'day', l: 'Daily log' }, { k: 'history', l: 'History' }, { k: 'career', l: 'Career log' }], tab, function (k) { tab = k; show(); })];
      A.mount(bar, kids);
    };
    var dayNav = h('div', { class: 'acts', style: 'margin-bottom:12px' });
    var show = function () {
      drawBar();
      if (tab === 'day') {
        var di = h('input', { class: 'in', type: 'date', value: day, style: 'width:auto', 'aria-label': 'Choose a date', onchange: function (e) { if (e.target.value) { day = e.target.value; show(); } } });
        A.mount(dayNav, [h('button', { class: 'icon-btn', 'aria-label': 'Previous day', onclick: function () { day = A.addDays(day, -1); show(); } }, A.icon('back')), di,
          h('button', { class: 'icon-btn', 'aria-label': 'Next day', onclick: function () { day = A.addDays(day, 1); show(); } }, A.icon('chev')),
          day !== A.S.today ? h('button', { class: 'btn soft sm', onclick: function () { day = A.S.today; show(); } }, 'Today') : null]);
        dayNav.classList.remove('hide'); A.mount(box, A.loading()); dayView(day, box);
      } else { dayNav.classList.add('hide'); A.mount(box, A.loading()); (tab === 'history' ? historyView : careerView)(box); }
    };
    show();
    return h('div', null, A.pageHead('Work and Tasks', 'Log what you do each day. Your best work builds your career record automatically.',
      h('button', { class: 'btn', onclick: function () { A.editLog(null, show, { date: day }); } }, A.icon('plus', 'sm'), 'New task')), bar, dayNav, box);
  };
})();
