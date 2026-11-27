// Runs in <head> before the CSS paints, so the saved theme is applied without a flash.
(function () {
  var saved = null;
  try { saved = localStorage.getItem('edufin-theme'); } catch (e) { /* storage blocked */ }
  var dark = saved ? saved === 'dark'
    : window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  if (dark) document.documentElement.classList.add('dark');
})();
