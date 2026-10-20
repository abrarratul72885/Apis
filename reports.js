/* Reports and Automation: preview, send, and the scheduled end-of-day email */
(function () {
  var h = A.h;
  var DAYS = [['Sun', 6], ['Mon', 0], ['Tue', 1], ['Wed', 2], ['Thu', 3], ['Fri', 4], ['Sat', 5]];

  A.views.reports = function () {
    var day = A.S.today;
    var preview = h('div'), auto = h('div'), hist = h('div');

    var loadPreview = function () {
      A.mount(preview, A.loading());
      Promise.all([A.get('/api/report/preview?date=' + day), A.get('/api/report/status')]).then(function (r) {
        var rep = r[0], st = r[1];
        var sendBtn = h('button', { class: 'btn', onclick: function (e) {
          if (!st.mail_ready) { A.toast('Connect Gmail first (Settings and Data).', true); return; }
          A.confirm('Send this report?', 'It will be emailed to: ' + (A.S.settings.report_to || 'the address in Settings') + (A.S.settings.attach_excel ? ', with the Excel file attached.' : '.'), 'Send now').then(function (y) {
            if (!y) return;
            A.busy(e.currentTarget, function () { return A.post('/api/report/send', { date: day }); }).then(function (x) { A.toast('Sent to ' + x.to.join(', ')); loadHist(); loadPreview(); }, A.fail);
          });
        } }, A.icon('mail', 'sm'), 'Send now');
        A.mount(preview, [
          h('div', { class: 'acts', style: 'margin-bottom:12px' }, sendBtn,
            h('button', { class: 'btn soft', onclick: function () { A.copy(rep.text); } }, 'Copy text'),
            h('button', { class: 'btn soft', onclick: function () { A.download('/api/export.xlsx?date=' + day); } }, A.icon('download', 'sm'), 'Excel for this day')),
          st.mail_ready ? null : h('button', { class: 'banner tap', style: 'margin-bottom:12px', onclick: function () { A.go('#/settings'); } }, 'Gmail is not connected yet. Tap to set it up in Settings. You can still copy the text or download the Excel file.'),
          h('div', { class: 'mail' }, h('div', { class: 'mh' }, h('div', { class: 'small mute' }, 'Subject'), h('div', { class: 't' }, rep.subject)), h('pre', null, rep.text)),
          !rep.stats.has_data ? h('p', { class: 'mute small', style: 'margin:10px 4px' }, 'Nothing is logged for this day, so the report is nearly empty. Add tasks in Work and Tasks first.') : null]);
        drawAuto(st);
      }, function (e) { A.mount(preview, h('div', { class: 'empty' }, e.message)); });
    };

    var drawAuto = function (st) {
      var s = A.S.settings, days = (s.eod_days || []).slice();
      var chips = h('div', { class: 'chips' }, DAYS.map(function (d) {
        var b = h('button', { type: 'button', class: 'chip' + (days.indexOf(d[1]) >= 0 ? ' on' : ''), 'aria-pressed': days.indexOf(d[1]) >= 0, onclick: function () {
          var i = days.indexOf(d[1]); if (i >= 0) days.splice(i, 1); else days.push(d[1]); b.classList.toggle('on', i < 0); b.setAttribute('aria-pressed', i < 0);
        } }, d[0]); return b;
      }));
      var f = A.form([
        { k: 'eod_enabled', label: 'Send my end-of-day report automatically', type: 'check', def: s.eod_enabled },
        { k: 'eod_time', label: 'Send at', type: 'time', half: true },
        { k: 'report_to', label: 'Send to (separate with commas)', ph: 'manager@company.com', help: 'Add at least one address.' },
        { k: 'attach_excel', label: 'Attach the Excel file', type: 'check' },
        { k: 'attach_full', label: 'Attach all data, not just today', type: 'check' }], s);
      var note = !st.mail_ready ? h('div', { class: 'banner', style: 'margin-bottom:12px' }, 'Automatic sending needs Gmail connected first.') :
        (st.enabled && st.next_run ? h('div', { class: 'banner good', style: 'margin-bottom:12px' }, 'Next automatic report: ' + A.date(st.next_run.slice(0, 10)) + ' at ' + st.next_run.slice(11) + (st.sent_today ? '. Today\'s was already sent.' : '')) : null);
      A.mount(auto, h('div', { class: 'card' }, h('h3', { class: 'h3', style: 'margin-bottom:6px' }, 'Automatic daily email'),
        h('p', { class: 'mute small', style: 'margin-bottom:12px' }, 'APIS sends the report from this laptop, so the laptop must be on and APIS running at that time. If it was off, APIS sends the missed report when you next open it.'),
        note, f.el, h('div', { class: 'f', style: 'margin-top:12px' }, h('label', { class: 'l' }, 'Send on these days'), chips),
        h('div', { class: 'acts', style: 'margin-top:14px' }, h('button', { class: 'btn', onclick: function (e) {
          var d = f.get(); d.eod_days = days; f.error('');
          A.busy(e.currentTarget, function () { return A.put('/api/settings', d); }).then(function (r) { A.S.settings = Object.assign(A.S.settings, r); A.toast('Saved'); loadPreview(); }, function (er) { f.error(er.message); });
        } }, 'Save'))));
    };

    var loadHist = function () {
      A.get('/api/sends').then(function (rows) {
        A.mount(hist, rows.length ? h('div', { class: 'group' }, rows.slice(0, 12).map(function (r) {
          return h('div', { class: 'row' }, h('div', { class: 'lead-ic', style: r.ok ? '' : 'background:var(--bad-t);color:var(--bad)' }, A.icon(r.ok ? 'check' : 'alert')),
            h('div', { class: 'grow' }, h('div', { class: 't' }, r.subject || 'Report'), h('div', { class: 's' }, r.at.slice(0, 16) + ' · ' + r.trigger + (r.ok ? ' · to ' + r.to_list : ' · ' + (r.error || 'failed')))));
        })) : h('div', { class: 'group' }, h('div', { class: 'empty' }, 'Nothing sent yet.')));
      }, function () { });
    };

    var di = h('input', { class: 'in', type: 'date', value: day, style: 'width:auto', 'aria-label': 'Report date', onchange: function (e) { if (e.target.value) { day = e.target.value; loadPreview(); } } });
    loadPreview(); loadHist();
    return h('div', null, A.pageHead('Reports and Automation', 'Your end-of-day report, ready to send or copy.', di),
      h('div', { class: 'two' }, h('div', null, preview), h('div', { class: 'stack' }, auto, h('div', null, h('div', { class: 'head', style: 'margin:10px 4px' }, h('h2', { class: 'h2' }, 'Sent reports')), hist))));
  };
})();
