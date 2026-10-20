/* My Portfolio: a LinkedIn-style profile that is entirely yours to edit */
(function () {
  var h = A.h;
  var CATS = ['Project', 'Achievement', 'Course', 'Competition', 'Volunteering', 'University', 'Work', 'Reading', 'Other'];
  var LINKICON = { LinkedIn: 'link', Instagram: 'image', Facebook: 'user', Website: 'globe', Blog: 'globe', GitHub: 'link', Other: 'link' };
  var D = null, tab = 'posts', filt = { q: '', cat: '', archived: false };

  /* ---------- editors ---------- */
  A.editProfile = function (done) {
    A.editor({
      title: 'Edit profile', values: A.S.profile, saveLabel: 'Save',
      fields: [
        { k: 'avatar', label: 'Profile photo', type: 'photo' }, { k: 'cover', label: 'Cover photo', type: 'photo', help: 'Wide pictures work best. Leave empty for the blue cover.' },
        { k: 'name', label: 'Full name', req: true }, { k: 'headline', label: 'Headline', ph: 'Marketing student | Data analyst | ...' },
        { k: 'location', label: 'Location', half: true }, { k: 'email', label: 'Email', type: 'email', half: true },
        { k: 'phone', label: 'Phone', half: true, help: 'Never shown on the public page.' }, { k: 'linkedin', label: 'LinkedIn link', half: true, ph: 'linkedin.com/in/...' },
        { k: 'about', label: 'About', type: 'area', rows: 9, help: 'Leave a blank line between paragraphs.' }],
      onSave: function (d) { return A.put('/api/profile', d); },
      done: function (p) { A.S.profile = p; A.refreshAvatar(); if (done) done(); }
    });
  };

  A.editPost = function (item, done, prefill) {
    var v = item ? Object.assign({}, item, { day: (item.posted_at || '').slice(0, 10) }) : Object.assign({ day: A.S.today, visibility: 'private', category: '' }, prefill || {});
    A.editor({
      title: item ? 'Edit post' : 'New post', values: v, saveLabel: item ? 'Save' : 'Post', done: done,
      fields: [
        { k: 'caption', label: 'What do you want to share?', type: 'area', rows: 6, ph: 'Describe what you did, what you learned, or what you achieved.' },
        { k: 'photos', label: 'Photos', type: 'photos' }, { k: 'docs', label: 'Documents (PDF)', type: 'docs', help: 'Certificates, reports or slides.' },
        { k: 'category', label: 'Category', half: true, list: CATS, ph: 'Choose or type' }, { k: 'day', label: 'Date', type: 'date', half: true },
        { k: 'tags', label: 'Tags', ph: 'marketing, sales, university', half: true }, { k: 'related', label: 'Related project or course', half: true, ph: 'Optional' },
        { k: 'link', label: 'Link', type: 'url', ph: 'https://...' },
        { k: 'visibility', label: 'Who can see it', type: 'select', opts: [{ v: 'private', l: 'Only me' }, { v: 'public', l: 'Public portfolio page' }], help: 'Public posts appear on the shareable page you create from here.' },
        { k: 'pinned', label: 'Pin to the top', type: 'check' }],
      onSave: function (d) {
        var t = item && item.posted_at && item.posted_at.length > 10 ? item.posted_at.slice(10) : ' 12:00';
        var body = Object.assign({}, d, { posted_at: d.day ? d.day + t : '' }); delete body.day;
        if (body.link && !/^https?:\/\//i.test(body.link)) body.link = 'https://' + body.link;
        return item ? A.put('/api/posts/' + item.id, body) : A.post('/api/posts', body);
      },
      onDelete: item ? function () { return A.del('/api/posts/' + item.id); } : null, deleteText: 'The post and its photos will be removed.'
    });
  };

  var EDIT = {
    experience: function (it, done) {
      A.editor({
        title: it ? 'Edit experience' : 'Add experience', values: it || { kind: 'Work' }, done: done,
        fields: [{ k: 'image', label: 'Organisation logo', type: 'photo', help: 'Upload the logo yourself so it looks right.' },
        { k: 'role', label: 'Role', req: true }, { k: 'org', label: 'Organisation', req: true }, { k: 'kind', label: 'Type', type: 'select', opts: A.S.enums.kinds, half: true }, { k: 'location', label: 'Location', half: true },
        { k: 'start', label: 'Started', type: 'month', req: true, half: true }, { k: 'end', label: 'Ended', type: 'month', half: true, help: 'Leave empty if you still do this.' },
        { k: 'description', label: 'What you did', type: 'area', rows: 5, help: 'Short sentences. The portfolio PDF uses the first few.' }, { k: 'skills', label: 'Skills used', ph: 'Excel, Leadership' }],
        onSave: function (d) { return it ? A.put('/api/experience/' + it.id, d) : A.post('/api/experience', d); }, onDelete: it ? function () { return A.del('/api/experience/' + it.id); } : null
      });
    },
    education: function (it, done) {
      A.editor({
        title: it ? 'Edit education' : 'Add education', values: it || {}, done: done,
        fields: [{ k: 'image', label: 'School logo', type: 'photo' }, { k: 'school', label: 'School or university', req: true }, { k: 'degree', label: 'Degree' }, { k: 'field', label: 'Major or field', half: true }, { k: 'grade', label: 'Result', half: true, ph: 'CGPA 3.30' },
        { k: 'start', label: 'Started', type: 'month', half: true }, { k: 'end', label: 'Ends or ended', type: 'month', half: true }, { k: 'description', label: 'Coursework, awards, activities', type: 'area', rows: 4 }],
        onSave: function (d) { return it ? A.put('/api/education/' + it.id, d) : A.post('/api/education', d); }, onDelete: it ? function () { return A.del('/api/education/' + it.id); } : null
      });
    },
    projects: function (it, done) {
      A.editor({
        title: it ? 'Edit project' : 'Add project', values: it || { kind: 'Academic', public: true }, done: done,
        fields: [{ k: 'image', label: 'Logo or cover picture', type: 'photo' }, { k: 'title', label: 'Project name', req: true }, { k: 'kind', label: 'Type', type: 'select', opts: A.S.enums.project_kinds, half: true }, { k: 'org', label: 'Organisation or course', half: true },
        { k: 'role', label: 'Your role', half: true }, { k: 'link', label: 'Link', half: true, ph: 'https://...' }, { k: 'start', label: 'Started', type: 'month', half: true }, { k: 'end', label: 'Ended', type: 'month', half: true },
        { k: 'summary', label: 'What it was', type: 'area', rows: 3 }, { k: 'problem', label: 'Problem it addressed', type: 'area', rows: 2 }, { k: 'methods', label: 'Methods and tools', type: 'area', rows: 2 },
        { k: 'results', label: 'Results and impact', type: 'area', rows: 3, help: 'Real numbers only.' }, { k: 'photos', label: 'Photos', type: 'photos' }, { k: 'tags', label: 'Tags' },
        { k: 'public', label: 'Show on my public page', type: 'check' }],
        onSave: function (d) { return it ? A.put('/api/projects/' + it.id, d) : A.post('/api/projects', d); }, onDelete: it ? function () { return A.del('/api/projects/' + it.id); } : null
      });
    },
    certs: function (it, done) {
      A.editor({
        title: it ? 'Edit certification' : 'Add certification', values: it || {}, done: done,
        fields: [{ k: 'image', label: 'Certificate picture or logo', type: 'photo' }, { k: 'title', label: 'Course or certificate', req: true }, { k: 'issuer', label: 'Issued by', half: true }, { k: 'issued', label: 'Issued', type: 'month', half: true },
        { k: 'credential_id', label: 'Credential ID', half: true }, { k: 'url', label: 'Credential link', half: true, ph: 'https://...' }, { k: 'skills', label: 'Skills learned' }, { k: 'description', label: 'Notes', type: 'area', rows: 3 }],
        onSave: function (d) { return it ? A.put('/api/certs/' + it.id, d) : A.post('/api/certs', d); }, onDelete: it ? function () { return A.del('/api/certs/' + it.id); } : null
      });
    },
    achievements: function (it, done, pre) {
      A.editor({
        title: it ? 'Edit achievement' : 'Add achievement', values: it || Object.assign({ kind: 'Award', public: true }, pre || {}), done: done,
        fields: [{ k: 'image', label: 'Picture or logo', type: 'photo' }, { k: 'title', label: 'Achievement', req: true }, { k: 'kind', label: 'Type', type: 'select', opts: A.S.enums.ach_kinds, half: true }, { k: 'date', label: 'When', type: 'month', half: true },
        { k: 'org', label: 'Organisation' }, { k: 'description', label: 'Details', type: 'area', rows: 4 }, { k: 'link', label: 'Link', ph: 'https://...' }, { k: 'public', label: 'Show on my public page', type: 'check' }],
        onSave: function (d) { return it ? A.put('/api/achievements/' + it.id, d) : A.post('/api/achievements', d); }, onDelete: it ? function () { return A.del('/api/achievements/' + it.id); } : null
      });
    },
    skills: function (it, done) {
      A.editor({
        title: it ? 'Edit skill' : 'Add skill', values: it || {}, done: done,
        fields: [{ k: 'name', label: 'Skill', req: true }, { k: 'category', label: 'Group', list: ['Analytics', 'Marketing', 'Creative', 'Leadership', 'Languages', 'Software'], ph: 'e.g. Analytics' }],
        onSave: function (d) { return it ? A.put('/api/skills/' + it.id, d) : A.post('/api/skills', d); }, onDelete: it ? function () { return A.del('/api/skills/' + it.id); } : null
      });
    },
    links: function (it, done) {
      A.editor({
        title: it ? 'Edit link' : 'Add link', values: it || { kind: 'LinkedIn' }, done: done,
        fields: [{ k: 'kind', label: 'Where', type: 'select', opts: A.S.enums.link_kinds }, { k: 'label', label: 'Name shown', ph: 'e.g. My blog', help: 'Optional. Leave empty to show the type.' }, { k: 'url', label: 'Link', req: true, ph: 'https://...' }],
        onSave: function (d) { d.url = A.url(d.url); return it ? A.put('/api/links/' + it.id, d) : A.post('/api/links', d); }, onDelete: it ? function () { return A.del('/api/links/' + it.id); } : null
      });
    }
  };

  /* ---------- pieces ---------- */
  function logo(img, icon) { return img ? h('img', { class: 'thumb', style: 'width:48px;height:48px;border-radius:10px;object-fit:contain;background:#fff;border:1px solid var(--line2);flex:none', src: A.file(img), alt: '' }) : h('div', { class: 'lead-ic', style: 'width:48px;height:48px' }, A.icon(icon)); }
  function editBtn(fn, label) { return h('button', { class: 'icon-btn edit-btn', 'aria-label': label || 'Edit', onclick: fn }, A.icon('edit', 'sm')); }
  function link(u, text) { return u ? h('a', { href: A.url(u), target: '_blank', rel: 'noopener' }, text || 'Open', ' ', A.icon('ext', 'sm')) : null; }
  function section(title, addLabel, onAdd, content, empty) {
    return h('div', { class: 'stack' }, h('div', { class: 'head', style: 'display:flex;justify-content:space-between;align-items:center;margin:0 4px' }, h('h2', { class: 'h2' }, title),
      h('button', { class: 'btn sm', onclick: onAdd }, A.icon('plus', 'sm'), addLabel)), content || h('div', { class: 'group' }, empty));
  }

  function postCard(x, refresh) {
    var p = A.S.profile, clamp = true;
    var cap = h('div', { class: 'cap clamp' }, (x.caption || '').split(/(#[\w]+)/).map(function (s) { return /^#/.test(s) ? h('span', { class: 'tag' }, s) : s; }));
    var more = (x.caption || '').length > 260 ? h('button', { class: 'more', onclick: function () { clamp = !clamp; cap.classList.toggle('clamp', clamp); more.textContent = clamp ? '...see more' : 'see less'; } }, '...see more') : null;
    if (!more) cap.classList.remove('clamp');
    var menu = h('button', { class: 'icon-btn', 'aria-label': 'Post options', onclick: function (e) { postMenu(e.currentTarget, x, refresh); } }, A.icon('more'));
    return h('article', { class: 'post' },
      h('div', { class: 'by' }, p.avatar ? h('img', { src: A.file(p.avatar), alt: '' }) : h('div', { class: 'avatar-btn' }, A.initials(p.name)),
        h('div', { class: 'grow' }, h('div', { class: 'n' }, p.name), h('div', { class: 'w' }, A.shortDate(x.posted_at), x.category ? A.pill(x.category, 'blue') : null, A.pill(x.visibility === 'public' ? 'Public' : 'Only me', x.visibility === 'public' ? 'good' : ''), x.pinned ? A.icon('pin', 'sm') : null, x.archived ? A.pill('Archived') : null)), menu),
      cap, more,
      x.related ? h('div', { class: 's small mute', style: 'margin-top:6px' }, 'Related: ' + x.related) : null,
      x.photos && x.photos.length ? h('div', { class: 'photos n' + Math.min(x.photos.length, 4) }, x.photos.slice(0, 4).map(function (f, i) {
        return h('button', { type: 'button', 'aria-label': 'Open photo ' + (i + 1), onclick: function () { A.lightbox(x.photos, i); } }, h('img', { src: A.file(f), alt: '', loading: 'lazy' }));
      })) : null,
      x.docs && x.docs.length ? h('div', { class: 'chips', style: 'margin-top:10px' }, x.docs.map(function (f, i) { return h('a', { class: 'chip', href: A.file(f), target: '_blank', rel: 'noopener' }, A.icon('file', 'sm'), 'Document ' + (i + 1)); })) : null,
      x.link ? h('div', { style: 'margin-top:10px' }, link(x.link, x.link.replace(/^https?:\/\//, '').slice(0, 50))) : null,
      x.tags ? h('div', { class: 'small mute', style: 'margin-top:8px' }, x.tags.split(',').map(function (t) { return '#' + t.trim().replace(/\s+/g, ''); }).join('  ')) : null);
  }
  function postMenu(anchor, x, refresh) {
    var m = h('div', { class: 'menu', role: 'menu' }), close = function () { m.remove(); document.removeEventListener('click', out, true); };
    var out = function (e) { if (!m.contains(e.target)) close(); };
    var it = function (icon, label, fn) { m.appendChild(h('button', { class: 'mi', role: 'menuitem', onclick: function () { close(); fn(); } }, A.icon(icon, 'sm'), label)); };
    it('edit', 'Edit', function () { A.editPost(x, refresh); });
    it('pin', x.pinned ? 'Unpin' : 'Pin to top', function () { A.put('/api/posts/' + x.id, { pinned: !x.pinned }).then(refresh, A.fail); });
    it('archive', x.archived ? 'Restore' : 'Archive', function () { A.put('/api/posts/' + x.id, { archived: !x.archived }).then(function () { A.toast(x.archived ? 'Restored' : 'Archived'); refresh(); }, A.fail); });
    it('award', 'Turn into an achievement', function () { EDIT.achievements(null, function () { A.toast('Added to Achievements'); refresh(); }, { title: (x.caption || '').split('\n')[0].slice(0, 120), description: x.caption.slice(0, 600) }); });
    document.body.appendChild(m); var r = anchor.getBoundingClientRect();
    m.style.top = (r.bottom + 6) + 'px'; m.style.right = Math.max(12, window.innerWidth - r.right) + 'px';
    setTimeout(function () { document.addEventListener('click', out, true); }, 0);
  }

  var TABS = [{ k: 'posts', l: 'Posts' }, { k: 'about', l: 'About' }, { k: 'experience', l: 'Experience' }, { k: 'education', l: 'Education' }, { k: 'projects', l: 'Projects' },
  { k: 'certs', l: 'Certifications' }, { k: 'achievements', l: 'Achievements' }, { k: 'skills', l: 'Skills' }, { k: 'links', l: 'Links' }];

  function content(refresh) {
    var p = A.S.profile;
    if (tab === 'posts') {
      var cats = Object.keys(D.posts.reduce(function (o, x) { if (x.category) o[x.category] = 1; return o; }, {}));
      var listBox = h('div');
      var drawList = function () {
        var posts = D.posts.filter(function (x) { return (filt.archived ? true : !x.archived) && (!filt.cat || x.category === filt.cat) && (!filt.q || ((x.caption || '') + ' ' + (x.tags || '')).toLowerCase().indexOf(filt.q.toLowerCase()) >= 0); });
        A.mount(listBox, posts.length ? posts.map(function (x) { return postCard(x, refresh); }) : h('div', { class: 'group' }, A.empty('No posts yet', 'Share what you are doing: a project, a course you finished, a competition.', h('button', { class: 'btn', onclick: function () { A.editPost(null, refresh); } }, 'Write your first post'))));
      };
      drawList();
      return h('div', null,
        h('button', { class: 'composer', onclick: function () { A.editPost(null, refresh); } }, p.avatar ? h('img', { src: A.file(p.avatar), alt: '' }) : h('div', { class: 'avatar-btn' }, A.initials(p.name)), h('div', { class: 'fake' }, 'Share a project, course or achievement...')),
        D.posts.length > 3 ? h('div', { class: 'filters', style: 'margin-bottom:12px' },
          h('input', { class: 'in', type: 'search', placeholder: 'Search posts', value: filt.q, 'aria-label': 'Search posts', style: 'max-width:260px', oninput: A.debounce(function (e) { filt.q = e.target.value; drawList(); }, 200) }),
          cats.length ? h('select', { class: 'in', style: 'width:auto', 'aria-label': 'Category', onchange: function (e) { filt.cat = e.target.value; drawList(); } }, [h('option', { value: '' }, 'All categories')].concat(cats.map(function (c) { return h('option', { value: c, selected: c === filt.cat }, c); }))) : null,
          h('button', { class: 'chip' + (filt.archived ? ' on' : ''), onclick: function (e) { filt.archived = !filt.archived; e.currentTarget.classList.toggle('on', filt.archived); drawList(); } }, 'Show archived')) : null,
        listBox);
    }
    if (tab === 'about') return h('div', { class: 'stack' }, h('div', { class: 'head', style: 'display:flex;justify-content:space-between;align-items:center;margin:0 4px' }, h('h2', { class: 'h2' }, 'About'), h('button', { class: 'btn sm', onclick: function () { A.editProfile(refresh); } }, A.icon('edit', 'sm'), 'Edit')),
      h('div', { class: 'group' }, p.about ? h('div', { class: 'about-text' }, p.about) : A.empty('Tell your story', 'A short summary of who you are and what you want to do.', h('button', { class: 'btn', onclick: function () { A.editProfile(refresh); } }, 'Write it'))));
    if (tab === 'experience') {
      var orgs = {}, order = []; D.experience.forEach(function (e) { var k = e.org.toLowerCase(); if (!orgs[k]) { orgs[k] = []; order.push(k); } orgs[k].push(e); });
      return section('Experience', 'Add', function () { EDIT.experience(null, refresh); }, order.length ? h('div', { class: 'group' }, order.map(function (k) {
        var items = orgs[k];
        return h('div', { class: 'org-block' }, h('div', { style: 'display:flex;gap:12px;align-items:center' }, logo(items.find(function (i) { return i.image; }) ? items.find(function (i) { return i.image; }).image : '', 'brief'), h('div', { class: 'org' }, items[0].org)),
          items.map(function (e) { return h('div', { class: 'role' }, h('div', { class: 't' }, e.role), h('div', { class: 's' }, e.kind + ' · ' + A.span(e.start, e.end) + (e.location ? ' · ' + e.location : '')), e.description ? h('p', null, e.description) : null, editBtn(function () { EDIT.experience(e, refresh); })); }));
      })) : null, A.empty('No experience added', 'Add jobs, internships, clubs and volunteering.'));
    }
    if (tab === 'education') return section('Education', 'Add', function () { EDIT.education(null, refresh); }, D.education.length ? h('div', { class: 'group' }, D.education.map(function (e) {
      return h('div', { class: 'row' }, logo(e.image, 'grad'), h('div', { class: 'grow' }, h('div', { class: 't' }, e.school), h('div', { class: 's' }, [e.degree, e.field].filter(Boolean).join(', ')), h('div', { class: 's' }, A.span(e.start, e.end) + (e.grade ? ' · ' + e.grade : '')), e.description ? h('p', { class: 's', style: 'white-space:pre-wrap;margin-top:4px' }, e.description) : null), editBtn(function () { EDIT.education(e, refresh); }));
    })) : null, A.empty('No education added', 'Add your university or school.'));
    if (tab === 'projects') return section('Projects', 'Add', function () { EDIT.projects(null, refresh); }, D.projects.length ? h('div', { class: 'group' }, D.projects.map(function (e) {
      return h('div', { class: 'row', style: 'align-items:flex-start' }, logo(e.image, 'folder'), h('div', { class: 'grow' }, h('div', { class: 't' }, e.title), h('div', { class: 's' }, [e.kind, e.org, e.role].filter(Boolean).join(' · ') + (e.start ? ' · ' + A.span(e.start, e.end) : '')),
        e.summary ? h('p', { style: 'margin-top:6px;white-space:pre-wrap' }, e.summary) : null, e.results ? h('p', { class: 's', style: 'margin-top:4px' }, 'Results: ' + e.results) : null, e.link ? h('div', { style: 'margin-top:6px' }, link(e.link)) : null,
        e.photos && e.photos.length ? h('div', { class: 'chips', style: 'margin-top:8px' }, e.photos.slice(0, 4).map(function (f, i) { return h('button', { class: 'chip', style: 'padding:0;overflow:hidden', 'aria-label': 'Open photo', onclick: function () { A.lightbox(e.photos, i); } }, h('img', { src: A.file(f), alt: '', style: 'width:64px;height:48px;object-fit:cover;display:block' })); })) : null), editBtn(function () { EDIT.projects(e, refresh); }));
    })) : null, A.empty('No projects yet', 'Add university projects, campaigns, competitions or personal work.'));
    if (tab === 'certs') return section('Licenses and certifications', 'Add', function () { EDIT.certs(null, refresh); }, D.certs.length ? h('div', { class: 'group' }, D.certs.map(function (c) {
      return h('div', { class: 'cert' }, c.image ? h('button', { class: 'thumb', 'aria-label': 'Open certificate', onclick: function () { A.lightbox([c.image], 0); } }, h('img', { src: A.file(c.image), alt: '' })) : h('div', { class: 'thumb' }, A.icon('award')),
        h('div', { class: 'grow' }, h('div', { class: 't' }, c.title), h('div', { class: 's' }, [c.issuer, A.month(c.issued)].filter(Boolean).join(' · ')), c.skills ? h('div', { class: 's' }, 'Skills: ' + c.skills) : null, c.url ? h('div', { style: 'margin-top:4px' }, link(c.url, 'Show credential')) : null), editBtn(function () { EDIT.certs(c, refresh); }));
    })) : null, A.empty('No certifications yet', 'Add every course you finish. APIS keeps them in date order.'));
    if (tab === 'achievements') return section('Achievements and activities', 'Add', function () { EDIT.achievements(null, refresh); }, D.achievements.length ? h('div', { class: 'group' }, D.achievements.map(function (e) {
      return h('div', { class: 'row', style: 'align-items:flex-start' }, logo(e.image, 'award'), h('div', { class: 'grow' }, h('div', { class: 't' }, e.title), h('div', { class: 's' }, [e.kind, e.org, A.month(e.date)].filter(Boolean).join(' · ')), e.description ? h('p', { style: 'margin-top:6px;white-space:pre-wrap' }, e.description) : null, e.link ? h('div', { style: 'margin-top:6px' }, link(e.link)) : null), editBtn(function () { EDIT.achievements(e, refresh); }));
    })) : null, A.empty('No achievements yet', 'Awards, leadership, competitions, publications, volunteering, memberships.'));
    if (tab === 'skills') {
      var cats2 = {}; D.skills.forEach(function (s) { (cats2[s.category || 'Other'] = cats2[s.category || 'Other'] || []).push(s); });
      return section('Skills', 'Add', function () { EDIT.skills(null, refresh); }, D.skills.length ? h('div', { class: 'group' }, Object.keys(cats2).map(function (c) {
        return h('div', { class: 'org-block' }, h('div', { class: 'org' }, c), h('div', { class: 'chips', style: 'margin-top:8px' }, cats2[c].map(function (s) { return h('button', { class: 'chip', onclick: function () { EDIT.skills(s, refresh); } }, s.name); })));
      })) : null, A.empty('No skills yet', 'Add the tools and strengths you want people to see.'));
    }
    return section('Links', 'Add', function () { EDIT.links(null, refresh); }, D.links.length ? h('div', { class: 'group' }, D.links.map(function (l) {
      return h('div', { class: 'row' }, h('div', { class: 'lead-ic' }, A.icon(LINKICON[l.kind] || 'link')), h('div', { class: 'grow' }, h('div', { class: 't' }, l.label || l.kind), h('div', { class: 's' }, l.url.replace(/^https?:\/\//, ''))),
        h('a', { class: 'btn soft sm', href: l.url, target: '_blank', rel: 'noopener' }, 'Open'), editBtn(function () { EDIT.links(l, refresh); }));
    })) : null, A.empty('No links yet', 'Add LinkedIn, Instagram, Facebook and your blog or website.'));
  }

  A.views.portfolio = function (parts) {
    if (parts[0] === 'build') return A.views.build();
    var wrap = h('div');
    var load = function () {
      return Promise.all(['posts', 'experience', 'education', 'projects', 'certs', 'achievements', 'skills', 'links'].map(function (e) { return A.get('/api/' + e); }).concat([A.get('/api/profile')])).then(function (r) {
        D = { posts: r[0], experience: r[1], education: r[2], projects: r[3], certs: r[4], achievements: r[5], skills: r[6], links: r[7] }; A.S.profile = r[8]; A.refreshAvatar();
      });
    };
    var draw = function () {
      var p = A.S.profile;
      var cover = h('div', { class: 'cover' }, p.cover ? h('img', { class: 'bg', src: A.file(p.cover), alt: '' }) : h('img', { class: 'wm', src: '/assets/logo.png', alt: '' }),
        h('button', { class: 'btn sm gray edit', onclick: function () { A.editProfile(refresh); } }, A.icon('edit', 'sm'), 'Edit'));
      var meta = [p.location, p.email, p.phone && p.phone].filter(Boolean);
      var head = h('div', { class: 'pf-head' },
        p.avatar ? h('img', { class: 'pf-avatar', src: A.file(p.avatar), alt: p.name, onclick: function () { A.lightbox([p.avatar], 0); } }) : h('div', { class: 'pf-avatar avatar-btn', style: 'font-size:34px' }, A.initials(p.name)),
        h('div', { class: 'pf-name' }, p.name), p.headline ? h('div', { class: 'pf-headline' }, p.headline) : null,
        h('div', { class: 'pf-meta' }, meta.map(function (m) { return h('span', null, m); }), D.links.slice(0, 5).map(function (l) { return h('a', { href: l.url, target: '_blank', rel: 'noopener' }, l.label || l.kind); }),
          !D.links.length && p.linkedin ? h('a', { href: A.url(p.linkedin), target: '_blank', rel: 'noopener' }, 'LinkedIn') : null),
        h('div', { class: 'pf-acts' }, h('button', { class: 'btn', onclick: function () { A.go('#/portfolio/build'); } }, A.icon('print', 'sm'), 'Make portfolio PDF'),
          h('button', { class: 'btn soft', onclick: share }, A.icon('globe', 'sm'), 'Share public page'), h('button', { class: 'btn gray', onclick: function () { A.editProfile(refresh); } }, 'Edit profile')));
      var tabs = h('div', { class: 'pf-tabs' }, A.seg(TABS, tab, function (k) { tab = k; A.mount(body, content(refresh)); }));
      var body = h('div', { style: 'margin-top:12px' }, content(refresh));
      draw.body = body;
      A.mount(wrap, [cover, head, tabs, body]);
    };
    var refresh = function (soft) { if (soft === true) { A.mount(draw.body, content(refresh)); return; } load().then(draw, A.fail); };
    var share = function () {
      var s = A.sheet({ title: 'Share your portfolio', body: h('div', { class: 'stack' },
        h('p', null, 'Make a public version of your portfolio for recruiters. It includes your profile, About, experience, education, certifications, public projects and achievements, public posts, skills and links. It does not include your phone number or anything marked Only me.'),
        h('ol', { class: 'steps' }, h('li', null, 'Download the portfolio folder below.'), h('li', null, 'Open netlify.com/drop in your browser (free) and drag the unzipped folder onto the page.'), h('li', null, 'You get a link to send to anyone. Download a fresh folder whenever you update.')),
        h('div', { class: 'acts' }, h('button', { class: 'btn', onclick: function (e) { A.busy(e.currentTarget, function () { return A.download('/api/publish.zip'); }).catch(A.fail); } }, A.icon('download', 'sm'), 'Download public folder'),
          h('a', { class: 'btn soft', href: '/cv', target: '_blank' }, 'One-page CV'))) });
    };
    return load().then(function () { draw(); return wrap; });
  };
})();
