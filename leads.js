/* Projects and Pipeline: client cards moving through four stages, with a document checklist */
(function () {
  var h = A.h;

  A.editLead = function (item, done) {
    A.editor({
      title: item ? 'Edit ' + A.W('client').toLowerCase() : 'New ' + A.W('client').toLowerCase(), values: item || {}, done: done, saveLabel: item ? 'Save' : 'Add',
      fields: [
        { k: 'company', label: A.W('client') + ' name', req: true, ph: 'Company or project name' },
        { k: 'contact', label: 'Contact person', half: true, ph: 'Optional' },
        { k: 'product', label: 'Product or purpose', half: true, ph: 'e.g. Working capital loan' },
        { k: 'amount', label: 'Amount (৳)', type: 'number', half: true },
        { k: 'next_action_date', label: 'Follow up on', type: 'date', half: true },
        { k: 'next_action', label: 'Next step', ph: 'e.g. Collect audited financials' },
        { k: 'notes', label: 'Notes', type: 'area', rows: 3 }],
      onSave: function (d) { return item ? A.put('/api/leads/' + item.id, d) : A.post('/api/leads', d); },
      onDelete: item ? function () { return A.del('/api/leads/' + item.id); } : null,
      deleteText: 'This also removes its document checklist.'
    });
  };

  function openLead(lead, refresh) {
    var stages = A.S.enums.stages;
    var body = h('div', { class: 'stack' });
    var cur = lead;
    var sheet;
    var draw = function () {
      A.get('/api/lead_docs?lead_id=' + cur.id).then(function (docs) {
        var msg = h('div', { class: 'banner hide', role: 'alert' });
        var stageBar = h('div', { class: 'seg', role: 'group', 'aria-label': 'Stage' }, stages.map(function (st) {
          return h('button', {
            type: 'button', class: st === cur.stage ? 'on' : '', onclick: function () {
              if (st === cur.stage) return;
              A.post('/api/leads/' + cur.id + '/move', { stage: st }).then(function (r) { cur = Object.assign(cur, r); refresh(); draw(); A.toast('Moved to ' + st); }, function (e) { msg.textContent = e.message; msg.classList.remove('hide'); });
            }
          }, st);
        }));
        var req = docs.filter(function (d) { return d.required; });
        var ver = req.filter(function (d) { return d.verified; }).length;
        var tgl = function (d, field, label) {
          return h('button', { type: 'button', class: 'tgl' + (d[field] ? ' on' : ''), 'aria-pressed': d[field] ? 'true' : 'false', onclick: function () {
            var patch = {}; patch[field] = !d[field];
            if (field === 'verified' && !d.verified) { patch.received = true; patch.received_date = d.received_date || A.S.today; }
            if (field === 'received' && !d.received) patch.received_date = A.S.today;
            if (field === 'received' && d.received) patch.verified = false;
            A.put('/api/lead_docs/' + d.id, patch).then(function () { refresh(); draw(); }, A.fail);
          } }, d[field] ? A.icon('check', 'sm') : null, label);
        };
        var today = A.S.today;
        A.mount(body, [
          h('div', null, h('div', { class: 'mute small', style: 'margin:0 4px 6px' }, 'Stage'), stageBar), msg,
          h('div', { class: 'card' }, h('div', { style: 'display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap' },
            h('div', null, h('div', { class: 'h3' }, cur.company), h('div', { class: 'mute' }, [cur.contact, cur.product].filter(Boolean).join(' · ') || 'No details yet')),
            h('div', { class: 'big num', style: 'font-size:28px' }, cur.amount ? A.money(cur.amount) : '')),
            cur.next_action ? h('div', { style: 'margin-top:10px' }, A.pill((cur.next_action_date ? A.shortDate(cur.next_action_date) + ': ' : '') + cur.next_action, cur.next_action_date && cur.next_action_date < today && cur.stage !== 'Sanctioned' ? 'bad' : 'blue')) : null,
            cur.notes ? h('p', { class: 'mute', style: 'margin-top:10px;white-space:pre-wrap' }, cur.notes) : null,
            h('div', { class: 'acts', style: 'margin-top:12px' }, h('button', { class: 'btn soft sm', onclick: function () { sheet.close(); A.editLead(cur, refresh); } }, A.icon('edit', 'sm'), 'Edit details'))),
          h('div', null, h('div', { class: 'head', style: 'display:flex;justify-content:space-between;align-items:baseline;margin:0 4px 8px' }, h('h3', { class: 'h3' }, 'Document checklist'),
            h('span', { class: 'small ' + (ver === req.length && req.length ? '' : 'mute'), style: ver === req.length && req.length ? 'color:var(--good);font-weight:650' : '' }, ver + ' of ' + req.length + ' required verified')),
            h('div', { class: 'group' }, docs.map(function (d) {
              var expired = d.expiry_date && d.expiry_date < today;
              return h('div', { class: 'docrow' }, h('div', { class: 'nm' }, d.doc, d.required ? h('span', { class: 'faint' }, ' *') : null,
                d.expiry_date ? h('div', { class: 's small ' + (expired ? '' : 'mute'), style: expired ? 'color:var(--bad)' : '' }, (expired ? 'Expired ' : 'Valid until ') + A.shortDate(d.expiry_date)) : null),
                tgl(d, 'received', 'Received'), tgl(d, 'verified', 'Verified'),
                h('button', { class: 'icon-btn', 'aria-label': 'Edit ' + d.doc, onclick: function () { editDoc(d); } }, A.icon('edit', 'sm')));
            })),
            h('div', { class: 'acts', style: 'margin-top:10px' }, h('button', { class: 'btn soft sm', onclick: function () { editDoc(null); } }, A.icon('plus', 'sm'), 'Add a document'), h('span', { class: 'small mute' }, '* required before Underwriting'))),
          A.S.settings.workspace === 'banking' ? h('div', { class: 'banner blue' }, 'Do not store customer NID numbers, account numbers or passwords here. Use short notes and anonymised names.') : null]);
      }, A.fail);
    };
    var editDoc = function (d) {
      A.editor({
        title: d ? d.doc : 'Add a document', values: d || { required: false }, done: function () { refresh(); draw(); }, toast: 'Saved',
        fields: [{ k: 'doc', label: 'Document', req: true, ph: 'e.g. Trade licence' }, { k: 'required', label: 'Required before Underwriting', type: 'check' },
        { k: 'received_date', label: 'Received on', type: 'date', half: true }, { k: 'expiry_date', label: 'Expires on', type: 'date', half: true }, { k: 'note', label: 'Note', ph: 'Optional' }],
        onSave: function (x) { return d ? A.put('/api/lead_docs/' + d.id, x) : A.post('/api/lead_docs', Object.assign({ lead_id: cur.id }, x)); },
        onDelete: d ? function () { return A.del('/api/lead_docs/' + d.id); } : null
      });
    };
    sheet = A.sheet({ title: lead.company, body: body, noFocus: true });
    draw();
  }

  A.views.pipeline = function () {
    var board = h('div');
    var load = function () {
      A.get('/api/leads').then(function (leads) {
        var stages = A.S.enums.stages, today = A.S.today;
        var tot = leads.reduce(function (s, l) { return s + (l.amount || 0); }, 0);
        var kids = [];
        kids.push(h('div', { class: 'tiles' }, stages.map(function (st) {
          var xs = leads.filter(function (l) { return l.stage === st; });
          return h('div', { class: 'tile' }, h('div', { class: 'k' }, st), h('div', { class: 'v num' }, xs.length), h('div', { class: 'd num' }, A.money(xs.reduce(function (s, l) { return s + (l.amount || 0); }, 0))));
        })));
        if (!leads.length) {
          kids.push(h('div', { class: 'group', style: 'margin-top:16px' }, A.empty('No ' + A.W('clients').toLowerCase() + ' yet', 'Add your first one. APIS creates the document checklist for you.', h('button', { class: 'btn', onclick: function () { A.editLead(null, load); } }, 'Add ' + A.W('client').toLowerCase()))));
        } else {
          kids.push(h('div', { class: 'board', style: 'margin-top:16px' }, stages.map(function (st) {
            var xs = leads.filter(function (l) { return l.stage === st; });
            return h('section', { class: 'col', 'aria-label': st }, h('div', { class: 'h' }, st, h('span', null, xs.length)),
              xs.length ? xs.map(function (l) {
                var late = l.next_action_date && l.next_action_date < today && st !== 'Sanctioned';
                return h('button', { class: 'lead-card', onclick: function () { openLead(l, load); } },
                  h('div', { class: 'co' }, l.company), l.amount ? h('div', { class: 'amt num' }, A.money(l.amount)) : null,
                  l.next_action ? h('div', { class: 's small', style: late ? 'color:var(--bad);font-weight:600' : 'color:var(--mute)' }, (late ? 'Overdue: ' : '') + l.next_action) : null,
                  l.docs_required ? h('div', null, h('div', { class: 'progress', 'aria-hidden': 'true' }, h('i', { style: 'width:' + Math.round(l.docs_verified / l.docs_required * 100) + '%' })), h('div', { class: 'small mute', style: 'margin-top:4px' }, l.docs_verified + ' of ' + l.docs_required + ' documents verified')) : null);
              }) : h('div', { class: 'small faint', style: 'padding:14px 8px' }, 'Nothing here'));
          })));
        }
        if (A.S.settings.workspace === 'banking') kids.push(h('div', { class: 'banner blue', style: 'margin-top:16px' }, 'Banking mode: keep records anonymised. Never enter customer NID numbers, account numbers or passwords. Check every figure against official bank reports.'));
        A.mount(board, kids);
      }, function (e) { A.mount(board, h('div', { class: 'empty' }, e.message)); });
    };
    load();
    return h('div', null, A.pageHead(A.W('pipeName'), A.W('clients') + ' move left to right. A document checklist protects each step.',
      h('button', { class: 'btn', onclick: function () { A.editLead(null, load); } }, A.icon('plus', 'sm'), 'New ' + A.W('client').toLowerCase())), board);
  };
})();
