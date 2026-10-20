/* Settings and Data: wording, Gmail, backups, phone access, PIN */
(function () {
  var h = A.h;
  var card = function (title, kids, lead) { return h('div', { class: 'card stack' }, h('h3', { class: 'h3' }, title), lead ? h('p', { class: 'small mute' }, lead) : null, kids); };
  var save = function (patch, msg) { return A.put('/api/settings', patch).then(function (s) { Object.assign(A.S.settings, s); A.toast(msg || 'Saved'); return s; }, A.fail); };

  A.views.settings = function () {
    var box = h('div', { class: 'stack' });
    var draw = function () {
      Promise.all([A.get('/api/settings'), A.get('/api/backup/status'), A.get('/api/network')]).then(function (r) {
        var s = r[0], b = r[1], n = r[2]; A.S.settings = s;
        /* work style */
        var ws = card('How you use APIS', [A.seg([{ k: 'sales', l: 'Sales and territory' }, { k: 'banking', l: 'Banking' }, { k: 'general', l: 'General' }], s.workspace, function (k) { save({ workspace: k }, 'Updated. Words and checklists will follow.').then(function () { A.reload(); }); }),
        h('p', { class: 'small mute' }, 'Changes the wording (Routes become Branches in banking) and the starting document checklist for new items. Your existing records are not changed. Banking mode never connects to bank systems.'),
        A.seg([{ k: 'auto', l: 'Match device' }, { k: 'light', l: 'Light' }, { k: 'dark', l: 'Dark' }], s.theme, function (k) { A.applyTheme(k); save({ theme: k }); })]);
        var al = h('input', { class: 'in', type: 'number', value: s.alert_threshold, min: 1, max: 200, style: 'max-width:120px', 'aria-label': 'Alert level' });
        var alertCard = card('Target alerts', [h('div', { class: 'acts' }, al, h('span', { class: 'mute' }, '% of target'), h('button', { class: 'btn soft sm', onclick: function () { save({ alert_threshold: +al.value }); } }, 'Save'))], 'Routes below this level show up on Home.');
        /* gmail */
        var gf = A.form([{ k: 'address', label: 'Your Gmail address', type: 'email', ph: 'you@gmail.com' }, { k: 'app_password', label: s.gmail_password_set ? 'App Password (saved, leave empty to keep)' : 'App Password', type: 'password', ph: '16 letters', help: 'Not your normal Gmail password. See the steps below.' },
        { k: 'report_to', label: 'Send reports to', ph: 'manager@company.com, me@gmail.com' }], { address: s.gmail_address, report_to: s.report_to });
        var gmail = card('Gmail for reports', [gf.el, h('div', { class: 'acts' }, h('button', { class: 'btn', onclick: function (e) {
          var d = gf.get(); gf.error('');
          A.busy(e.currentTarget, function () { return A.put('/api/gmail', d); }).then(function (x) { Object.assign(A.S.settings, x); A.toast('Gmail saved'); draw(); }, function (er) { gf.error(er.message); });
        } }, 'Save'), s.gmail_password_set ? h('button', { class: 'btn soft', onclick: function (e) { A.busy(e.currentTarget, function () { return A.post('/api/mail/test'); }).then(function (x) { A.toast('Test email sent to ' + x.to); }, A.fail); } }, 'Send a test email') : null,
          s.gmail_password_set ? h('button', { class: 'btn danger', onclick: function () { A.confirm('Disconnect Gmail?', 'The saved App Password is erased and automatic emails stop.', 'Disconnect', true).then(function (y) { if (y) A.del('/api/gmail').then(draw, A.fail); }); } }, 'Disconnect') : null),
        h('details', { class: 'guide' }, h('summary', null, 'How to get an App Password (2 minutes)', A.icon('chev', 'sm')), h('ol', { class: 'steps' },
          h('li', null, 'Open myaccount.google.com/security and turn on 2-Step Verification if it is off.'), h('li', null, 'Search "App passwords" on that page and open it.'), h('li', null, 'Name it APIS and press Create.'), h('li', null, 'Copy the 16 letters Google shows and paste them above. Spaces are fine.'), h('li', null, 'Press Save, then Send a test email.')))], 'APIS sends your end-of-day report through your own Gmail. The password is stored only on this laptop.');
        /* backup */
        var dd = h('input', { class: 'in', type: 'text', value: s.drive_dir || '', placeholder: 'e.g. C:\\Users\\You\\Google Drive\\APIS Backup', 'aria-label': 'Google Drive folder' });
        var backup = card('Backup and data', [
          h('div', { class: 'banner ' + (b.last_backup ? 'good' : '') }, b.last_backup ? 'Last backup on this laptop: ' + b.last_backup : 'No backup yet. One is made automatically every few hours.'),
          h('div', { class: 'small mute' }, 'Everything is saved on this laptop in: ' + n.data),
          h('div', { class: 'f', style: 'display:flex;flex-direction:column;gap:6px' }, h('label', { class: 'small mute' }, 'Google Drive backup folder'), dd,
            b.detected && b.detected.length ? h('div', { class: 'chips' }, b.detected.map(function (p) { return h('button', { class: 'chip', onclick: function () { dd.value = p; } }, p); })) : null,
            b.last_drive_error ? h('div', { class: 'banner bad' }, b.last_drive_error) : (b.last_drive_backup ? h('div', { class: 'small', style: 'color:var(--good)' }, 'Last copy to Drive: ' + b.last_drive_backup) : null)),
          h('div', { class: 'acts' }, h('button', { class: 'btn', onclick: function (e) { A.busy(e.currentTarget, function () { return A.put('/api/settings', { drive_dir: dd.value }).then(function () { return A.post('/api/backup/run'); }); }).then(function (x) { A.toast(x.drive_error ? 'Backup made, but Drive failed' : 'Backup complete'); draw(); }, A.fail); } }, A.icon('folder', 'sm'), 'Save and back up now'),
            h('button', { class: 'btn soft', onclick: function () { A.download('/api/export.xlsx?scope=all'); } }, A.icon('download', 'sm'), 'Export everything to Excel'))],
          'Install Google Drive for desktop, pick a folder inside it above, and every backup is copied there. To restore on a new laptop, copy the "database" file back into APIS\\data (steps are in READ ME FIRST).');
        /* phone */
        var phone = card('Use APIS on your phone and tablet', [
          n.urls.length ? n.urls.map(function (u) { return h('div', { class: 'urlbox' }, u); }) : h('div', { class: 'banner' }, 'No Wi-Fi address found. Connect the laptop to Wi-Fi.'),
          h('ol', { class: 'steps' }, h('li', null, 'Keep APIS running on the laptop and connect the phone to the same Wi-Fi.'), h('li', null, 'Open Chrome on the phone and type the address above.'), h('li', null, 'Sign in with your PIN.'), h('li', null, 'Tap the three dots, then "Install app" or "Add to Home screen".'))],
          'Works only while the laptop is on and on the same network.');
        /* pin */
        var pf = A.form([{ k: 'old', label: 'Current PIN', type: 'password' }, { k: 'new', label: 'New PIN (4 or more)', type: 'password' }]);
        var pin = card('PIN', [pf.el, h('div', { class: 'acts' }, h('button', { class: 'btn', onclick: function (e) { var d = pf.get(); pf.error(''); A.busy(e.currentTarget, function () { return A.post('/api/auth/change', d); }).then(function () { A.toast('PIN changed'); draw(); }, function (er) { pf.error(er.message); }); } }, 'Change PIN'),
          h('button', { class: 'btn gray', onclick: function () { A.post('/api/auth/logout').then(A.onLoggedOut); } }, A.icon('lock', 'sm'), 'Lock now'))]);
        var about = card('About', [h('div', { class: 'small mute' }, 'APIS version ' + (A.S.version || "")), h('div', { class: 'acts' }, h('button', { class: 'btn danger sm', onclick: function () { A.confirm('Stop APIS?', 'APIS closes on the laptop. Double-click Start APIS to open it again.', 'Stop APIS', true).then(function (y) { if (y) A.post('/api/shutdown').then(function () { A.mount(document.getElementById('root'), h('div', { class: 'empty' }, h('b', null, 'APIS has stopped'), h('div', null, 'You can close this tab.'))); }); }); } }, 'Stop APIS'))]);
        A.mount(box, [h('div', { class: 'two' }, h('div', { class: 'stack' }, ws, alertCard, gmail), h('div', { class: 'stack' }, backup, phone, pin, about))]);
      }, function (e) { A.mount(box, h('div', { class: 'empty' }, e.message)); });
    };
    draw();
    return h('div', null, A.pageHead('Settings and Data', 'Everything you can change lives here.'), box);
  };
})();
