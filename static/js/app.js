// EduFin front-end behaviour. Loaded as an external file: the CSP forbids inline scripts.
(function () {
  'use strict';
  var root = document.documentElement;
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Dark / light mode toggle
  var toggle = document.querySelector('[data-theme-toggle]');
  function syncToggle() {
    if (!toggle) return;
    var dark = root.classList.contains('dark');
    toggle.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
    toggle.setAttribute('aria-pressed', dark ? 'true' : 'false');
  }
  if (toggle) {
    syncToggle();
    toggle.addEventListener('click', function () {
      root.classList.add('theme-anim');
      var dark = root.classList.toggle('dark');
      try { localStorage.setItem('edufin-theme', dark ? 'dark' : 'light'); } catch (e) { /* ignore */ }
      syncToggle();
      window.setTimeout(function () { root.classList.remove('theme-anim'); }, 400);
    });
  }

  // Mobile navigation
  var navToggle = document.querySelector('[data-nav-toggle]');
  var nav = document.getElementById('main-nav');
  if (navToggle && nav) {
    navToggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // Toasts: dismiss on click, fade out after a few seconds
  document.querySelectorAll('[data-toast]').forEach(function (toast) {
    function hide() {
      toast.classList.add('hide');
      window.setTimeout(function () { toast.remove(); }, 400);
    }
    var close = toast.querySelector('[data-toast-close]');
    if (close) close.addEventListener('click', hide);
    window.setTimeout(hide, 5000);
  });

  // Reveal-on-scroll
  var revealables = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && !reduceMotion) {
    root.classList.add('js-reveal');
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('in');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08 });
    revealables.forEach(function (el, i) {
      el.classList.add('d' + Math.min(i, 6));
      io.observe(el);
    });
    // Safety net: never leave content hidden if the observer does not fire.
    window.setTimeout(function () {
      revealables.forEach(function (el) { el.classList.add('in'); });
    }, 1500);
  }

  // Count-up animation for the dashboard numbers
  function animateCount(el) {
    var target = parseFloat(el.getAttribute('data-count'));
    if (isNaN(target)) return;
    var text = el.textContent.trim();
    var match = text.match(/^(-?)(\D*?)\s?[\d,.]+$/);
    var prefix = match ? match[2] : '';
    var decimals = /\.\d\d$/.test(text) ? 2 : 0;
    var start = null;
    var duration = 900;
    function frame(ts) {
      if (start === null) start = ts;
      var p = Math.min((ts - start) / duration, 1);
      var eased = 1 - Math.pow(1 - p, 3);
      var value = target * eased;
      var sign = value < 0 ? '-' : '';
      el.textContent = sign + prefix + ' ' + Math.abs(value).toLocaleString('en-US', {
        minimumFractionDigits: decimals, maximumFractionDigits: decimals
      });
      if (p < 1) window.requestAnimationFrame(frame);
      else el.textContent = text;
    }
    window.requestAnimationFrame(frame);
  }
  if (!reduceMotion) document.querySelectorAll('[data-count]').forEach(animateCount);

  // Transaction form: only show categories that match income / expense
  var form = document.querySelector('[data-tx-form]');
  if (form) {
    var select = form.querySelector('[data-category-select]');
    var radios = form.querySelectorAll('input[name="kind"]');
    var groups = {};
    if (select) {
      select.querySelectorAll('optgroup').forEach(function (g) {
        groups[g.label.toLowerCase()] = g;
      });
    }
    function filterCategories() {
      var checked = form.querySelector('input[name="kind"]:checked');
      if (!checked || !select) return;
      Object.keys(groups).forEach(function (key) {
        var show = key === checked.value;
        groups[key].hidden = !show;
        groups[key].disabled = !show;
      });
      var opt = select.options[select.selectedIndex];
      if (opt && opt.parentNode && opt.parentNode.disabled) select.value = '';
    }
    radios.forEach(function (r) { r.addEventListener('change', filterCategories); });
    filterCategories();
  }

  // Confirmation for small destructive forms (budget removal)
  document.querySelectorAll('[data-confirm]').forEach(function (btn) {
    btn.addEventListener('click', function (event) {
      if (!window.confirm(btn.getAttribute('data-confirm'))) event.preventDefault();
    });
  });

  // Rotating money tips on the dashboard
  var tip = document.querySelector('[data-tips]');
  if (tip) {
    var tips = [
      tip.textContent,
      'Record spending the same day: small daily costs are the easiest to forget.',
      'Keep one month of essential costs as an emergency fund.',
      'Divide next term’s fees by the months left and save that amount each month.',
      'Check your data and airtime budget weekly; it is the most common leak.'
    ];
    var i = 0;
    window.setInterval(function () {
      i = (i + 1) % tips.length;
      tip.classList.add('swap');
      window.setTimeout(function () {
        tip.textContent = tips[i];
        tip.classList.remove('swap');
      }, 300);
    }, 8000);
  }
})();
