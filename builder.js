/* Portfolio Builder: choose what goes in, preview it, save as PDF / HTML / Word */
(function () {
  var h = A.h;
  var KEY = 'apis_pf_cfg';
  var SEC = { summary: 'Profile summary', experience: 'Experience and leadership', education: 'Education', projects: 'Projects', certifications: 'Certifications', achievements: 'Achievements', skills: 'Skills', links: 'Links' };

  A.views.build = function () {
    var cfg = null, opts = null, ents = null, timer = null, frame, info = h('div', { class: 'stack' });
    var sectionBox = h('div'), picksBox = h('div');
    try { cfg = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e) { }
    var persist = function () { try { localStorage.setItem(KEY, JSON.stringify(cfg)); } catch (e) { } };
    var refresh = function () { persist(); clearTimeout(timer); timer = setTimeout(preview, 350); };

    var preview = function () {
      A.post('/api/portfolio/preview', cfg).then(function (r) {
        frame.srcdoc = r.html;
        var ok = r.pages <= cfg.pages + 0.15;
        A.mount(info, [
          h('div', { class: 'banner ' + (ok ? 'good' : '') }, 'This will print as ' + r.pages_text + (cfg.fit ? '' : '. Automatic fitting is off.') + '.'),
          r.notes.length ? h('div', { class: 'small mute' }, r.notes.join(' ')) : null,
          r.dropped.length ? h('div', { class: 'small mute' }, h('b', null, 'Left out to fit: '), r.dropped.map(function (d) { return d.title; }).join('; '), '. Nothing was deleted from your records. Tick them under "Choose entries" and switch off automatic fitting if you want everything.') : null,
          r.empty_sections.length ? h('div', { class: 'small mute' }, 'Empty sections skipped: ' + r.empty_sections.map(function (k) { return SEC[k]; }).join(', ') + '.') : null]);
      }, function (e) { A.mount(info, h('div', { class: 'banner bad' }, e.message)); });
    };
    var sizeFrame = function () { try { frame.style.height = (frame.contentDocument.documentElement.scrollHeight + 8) + 'px'; } catch (e) { } };

    var drawSections = function () {
      A.mount(sectionBox, cfg.sections.map(function (s, i) {
        return h('div', { class: 'row', style: 'min-height:48px;padding:8px 14px' },
          h('label', { class: 'switch', style: 'background:none;padding:0;flex:1;min-height:0' }, h('span', null, SEC[s.key]), h('input', { type: 'checkbox', checked: s.on, onchange: function (e) { s.on = e.target.checked; refresh(); } })),
          h('button', { class: 'icon-btn', 'aria-label': 'Move up', disabled: i === 0, onclick: function () { cfg.sections.splice(i - 1, 0, cfg.sections.splice(i, 1)[0]); drawSections(); refresh(); } }, A.icon('back', 'sm')),
          h('button', { class: 'icon-btn', 'aria-label': 'Move down', disabled: i === cfg.sections.length - 1, onclick: function () { cfg.sections.splice(i + 1, 0, cfg.sections.splice(i, 1)[0]); drawSections(); refresh(); } }, A.icon('chev', 'sm')));
      }));
      Array.prototype.forEach.call(sectionBox.querySelectorAll('button[disabled]'), function (b) { b.style.opacity = .3; });
    };
    var drawPicks = function () {
      var defs = [['experience', 'Experience', 'experience', function (x) { return x.role + ', ' + x.org; }], ['projects', 'Projects', 'projects', function (x) { return x.title; }],
      ['certifications', 'Certifications', 'certs', function (x) { return x.title; }], ['achievements', 'Achievements', 'achievements', function (x) { return x.title; }]];
      A.mount(picksBox, defs.map(function (d) {
        var list = ents[d[2]] || [];
        if (!list.length) return null;
        var ex = cfg.exclude[d[0]] = cfg.exclude[d[0]] || [];
        return h('details', { class: 'guide', style: 'margin-bottom:8px' }, h('summary', null, d[1], h('span', { class: 'mute small' }, list.length - ex.length + ' of ' + list.length)),
          h('div', { class: 'stack', style: 'padding-bottom:12px' }, list.map(function (x) {
            return h('label', { class: 'switch', style: 'background:var(--surface2)' }, h('span', { class: 'small' }, d[3](x)), h('input', { type: 'checkbox', checked: ex.indexOf(x.id) < 0, onchange: function (e) { var i = ex.indexOf(x.id); if (e.target.checked && i >= 0) ex.splice(i, 1); if (!e.target.checked && i < 0) ex.push(x.id); refresh(); } }));
          })));
      }));
    };
    var chk = function (label, get, set) { return h('label', { class: 'switch' }, h('span', null, label), h('input', { type: 'checkbox', checked: get(), onchange: function (e) { set(e.target.checked); refresh(); } })); };

    var wrap = h('div');
    var url = function () { return '/portfolio-print?c=' + encodeURIComponent(JSON.stringify(cfg)); };

    Promise.all([A.get('/api/portfolio/options'), A.get('/api/experience'), A.get('/api/projects'), A.get('/api/certs'), A.get('/api/achievements'), A.get('/api/profile')]).then(function (r) {
      opts = r[0]; ents = { experience: r[1], projects: r[2], certs: r[3], achievements: r[4] };
      if (!cfg) cfg = JSON.parse(JSON.stringify(opts.default));
      cfg.contact = Object.assign({}, opts.default.contact, cfg.contact || {}); cfg.exclude = cfg.exclude || {};
      var segRow = function (label, items, key, conv) { return h('div', null, h('div', { class: 'mute small', style: 'margin:0 4px 6px' }, label), A.seg(items, String(cfg[key]), function (k) { cfg[key] = conv ? conv(k) : k; if (key === 'template') { cfg.accent = ''; } refresh(); })); };
      var accent = h('input', { type: 'color', value: cfg.accent || (opts.templates.filter(function (t) { return t.key === cfg.template; })[0] || {}).accent || '#0a57cc', 'aria-label': 'Accent colour', style: 'width:48px;height:36px;border:0;background:none', onchange: function (e) { cfg.accent = e.target.value; refresh(); } });
      frame = h('iframe', { title: 'Portfolio preview', sandbox: 'allow-same-origin', style: 'width:100%;border:0;min-height:900px;background:#e9e9ee;border-radius:16px', onload: sizeFrame });
      var summary = h('textarea', { class: 'in', rows: 4, placeholder: 'Leave empty to use the start of your About text. Your saved About is never changed.', 'aria-label': 'Profile summary text', style: 'min-height:90px', oninput: A.debounce(function (e) { cfg.summary = e.target.value; refresh(); }, 300) }); summary.value = cfg.summary || '';
      var headline = h('input', { class: 'in', type: 'text', placeholder: 'Uses your profile headline if empty', 'aria-label': 'Headline for this portfolio', oninput: A.debounce(function (e) { cfg.headline = e.target.value; refresh(); }, 300) }); headline.value = cfg.headline || '';
      var controls = h('div', { class: 'stack' },
        h('div', { class: 'card stack' },
          h('div', null, h('div', { class: 'mute small', style: 'margin:0 4px 6px' }, 'Who is this for?'), h('select', { class: 'in', 'aria-label': 'Purpose', onchange: function (e) { cfg.purpose = e.target.value; refresh(); } }, opts.purposes.map(function (p) { return h('option', { value: p.key, selected: p.key === cfg.purpose }, p.label); }))),
          segRow('Length', [{ k: '2', l: '2 pages' }, { k: '3', l: '3 pages' }], 'pages', Number), segRow('Template', opts.templates.map(function (t) { return { k: t.key, l: t.label.split(' ')[0] }; }), 'template'),
          segRow('Detail', [{ k: 'brief', l: 'Brief' }, { k: 'standard', l: 'Standard' }, { k: 'full', l: 'Full' }], 'detail'), segRow('Font', [{ k: 'sans', l: 'Modern' }, { k: 'serif', l: 'Classic' }], 'font'),
          h('div', { class: 'acts' }, h('span', { class: 'mute small' }, 'Accent colour'), accent, h('button', { class: 'btn plain sm', onclick: function () { cfg.accent = ''; accent.value = (opts.templates.filter(function (t) { return t.key === cfg.template; })[0] || {}).accent; refresh(); } }, 'Reset'))),
        h('div', { class: 'card stack' }, h('h3', { class: 'h3' }, 'Show'), chk('Fit to the page length automatically', function () { return cfg.fit; }, function (v) { cfg.fit = v; }), chk('Profile photo', function () { return cfg.photo; }, function (v) { cfg.photo = v; }),
          chk('Organisation logos', function () { return cfg.logos; }, function (v) { cfg.logos = v; }), chk('Colour band at the top', function () { return cfg.cover; }, function (v) { cfg.cover = v; })),
        h('div', { class: 'card stack' }, h('h3', { class: 'h3' }, 'Contact details'), h('p', { class: 'small mute' }, 'Untick anything private before you share the file.'),
          chk('Email', function () { return cfg.contact.email; }, function (v) { cfg.contact.email = v; }), chk('Phone number', function () { return cfg.contact.phone; }, function (v) { cfg.contact.phone = v; }),
          chk('Location', function () { return cfg.contact.location; }, function (v) { cfg.contact.location = v; }), chk('LinkedIn and links', function () { return cfg.contact.links; }, function (v) { cfg.contact.links = v; })),
        h('div', { class: 'card stack' }, h('h3', { class: 'h3' }, 'Sections and order'), h('div', { class: 'group' }, sectionBox)),
        h('div', { class: 'card stack' }, h('h3', { class: 'h3' }, 'Choose entries'), h('p', { class: 'small mute' }, 'Untick anything you do not want in this version. Your records stay as they are.'), picksBox),
        h('div', { class: 'card stack' }, h('h3', { class: 'h3' }, 'Edit the words (this version only)'), headline, summary));
      var actions = h('div', { class: 'acts' },
        h('button', { class: 'btn', onclick: function () { persist(); window.open(url(), '_blank'); } }, A.icon('print', 'sm'), 'Save as PDF'),
        h('button', { class: 'btn soft', onclick: function (e) { A.busy(e.currentTarget, function () { return A.download('/api/portfolio/export/docx', cfg); }).catch(A.fail); } }, A.icon('download', 'sm'), 'Word'),
        h('button', { class: 'btn soft', onclick: function (e) { A.busy(e.currentTarget, function () { return A.download('/api/portfolio/export/html', cfg); }).catch(A.fail); } }, A.icon('download', 'sm'), 'HTML'));
      A.mount(wrap, h('div', { class: 'two', style: 'grid-template-columns:minmax(0,380px) minmax(0,1fr)' }, controls, h('div', { class: 'stack' }, actions, info, frame,
        h('p', { class: 'small faint' }, 'In the print window choose "Save as PDF", keep margins on Default and turn off "Headers and footers". The page count is a target: APIS never invents content or shrinks text until it is unreadable.'))));
      drawSections(); drawPicks(); preview();
    }).catch(function (e) { A.mount(wrap, h('div', { class: 'empty' }, e.message)); });
    return h('div', null, A.pageHead('Portfolio Builder', 'A clean 2 to 3 page portfolio made from your saved records.', h('button', { class: 'btn gray', onclick: function () { A.go('#/portfolio'); } }, A.icon('back', 'sm'), 'Back to profile')), wrap);
  };
})();
