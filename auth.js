/* Sign-in and first-time PIN setup */
(function () {
  var h = A.h;
  A.showLogin = function (setup) {
    var root = document.getElementById('root');
    var pin = h('input', { class: 'pin', type: 'password', inputmode: 'numeric', autocomplete: setup ? 'new-password' : 'current-password', placeholder: setup ? 'Choose a PIN (4 or more)' : 'Your PIN', 'aria-label': 'PIN', maxlength: 32 });
    var pin2 = setup ? h('input', { class: 'pin', type: 'password', inputmode: 'numeric', autocomplete: 'new-password', placeholder: 'Type it again', 'aria-label': 'Repeat PIN', maxlength: 32 }) : null;
    var err = h('div', { class: 'err', role: 'alert' });
    var btn = h('button', { class: 'btn block', type: 'submit' }, setup ? 'Create PIN and open APIS' : 'Open APIS');
    var form = h('form', {
      onsubmit: function (e) {
        e.preventDefault(); err.textContent = '';
        if (setup && pin.value !== pin2.value) { err.textContent = 'The two PINs are not the same.'; return; }
        A.busy(btn, function () { return A.post(setup ? '/api/auth/setup' : '/api/auth/login', { pin: pin.value }); })
          .then(function () { return A.start(); }, function (e2) { err.textContent = e2.message; pin.select(); });
      }
    },
      h('img', { class: 'mark', src: '/assets/logo.png', alt: 'APIS' }),
      h('h1', null, setup ? 'Welcome to APIS' : 'APIS'),
      h('p', { class: 'mute' }, setup ? 'Set a PIN to keep your work private. You will type it when you open APIS on any device.' : 'Work Smarter. Make an Impact.'),
      pin, pin2, err, btn,
      setup ? h('p', { class: 'small faint' }, 'Write your PIN down somewhere safe. It cannot be recovered, but you can reset it from the Windows folder if you forget (see READ ME FIRST).') : null);
    A.mount(root, h('div', { class: 'login' }, h('div', { class: 'art' }, h('img', { src: '/assets/mascot.jpg', alt: '' })), h('div', { class: 'panel' }, form)));
    setTimeout(function () { pin.focus(); }, 50);
  };
})();
