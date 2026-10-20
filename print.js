document.addEventListener('click', function (e) {
  var b = e.target.closest && e.target.closest('[data-print]');
  if (b) window.print();
});
