/* ==========================================================================
   static/js/404.js  |  TalentSync 404 page interactivity
   ========================================================================== */
(function () {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Theme (saved choice > system preference > dark) ---------- */
  var root = document.documentElement;
  function applyTheme(t) { root.setAttribute('data-theme', t); }
  var saved = null;
  try { saved = localStorage.getItem('ts-theme'); } catch (e) {}
  var systemLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
  applyTheme(saved || (systemLight ? 'light' : 'dark'));

  var toggleBtn = $('theme-toggle-btn');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', function () {
      var next = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
      applyTheme(next);
      try { localStorage.setItem('ts-theme', next); } catch (e) {}
    });
  }

  /* ---------- Toast ---------- */
  var toast = $('toast'), toastMsg = $('toast-message'), toastTimer;
  function showToast(msg) {
    if (!toast || !toastMsg) return;
    toastMsg.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.classList.remove('show'); }, 2000);
  }

  /* ---------- Requested path + copy ---------- */
  var chip = $('failed-url-chip');
  if (chip) chip.textContent = location.pathname + location.search;

  var yr = $('copyright-year');
  if (yr) yr.textContent = new Date().getFullYear();

  var copyBtn = $('copy-url-btn');
  if (copyBtn) {
    copyBtn.addEventListener('click', function () {
      var url = location.href;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(
          function () { showToast('Link copied to clipboard'); },
          function () { showToast('Copy failed'); }
        );
      } else {
        var ta = document.createElement('textarea');
        ta.value = url; document.body.appendChild(ta); ta.select();
        try { document.execCommand('copy'); showToast('Link copied to clipboard'); }
        catch (e) { showToast('Copy failed'); }
        document.body.removeChild(ta);
      }
    });
  }

  /* ---------- Go back ---------- */
  var redirectBox = $('redirect-container');
  var home = redirectBox ? (redirectBox.getAttribute('data-home') || '/') : '/';
  var backBtn = $('go-back-btn');
  if (backBtn) {
    backBtn.addEventListener('click', function () {
      if (history.length > 1 && document.referrer) history.back();
      else location.href = home;
    });
  }

  /* ---------- Auto-redirect countdown ---------- */
  var stopRedirect = function () {};   // safe default, real version set below
  var box = $('redirect-container');
  if (box) {
    var total = parseInt(box.getAttribute('data-timeout'), 10) || 15;
    var left = total, timer = null, CIRC = 100.53;
    var ring = $('countdown-circle'), num = $('countdown-number'), inline = $('countdown-text-inline');

    function render() {
      if (num) num.textContent = left;
      if (inline) inline.textContent = left + (left === 1 ? ' second' : ' seconds');
      if (ring) ring.style.strokeDashoffset = CIRC * (1 - left / total);
    }

    stopRedirect = function () {
      if (timer) { clearInterval(timer); timer = null; }
      box.classList.add('is-stopped');
    };

    if (reduceMotion) {
      box.classList.add('is-stopped');
    } else {
      render();
      timer = setInterval(function () {
        left -= 1; render();
        if (left <= 0) { clearInterval(timer); location.href = home; }
      }, 1000);
    }

    var cancelBtn = $('cancel-redirect-btn');
    if (cancelBtn) cancelBtn.addEventListener('click', stopRedirect);
  }

  /* ---------- Shortcut filter ---------- */
  var input = $('shortcut-filter-input');
  var cards = Array.prototype.slice.call(document.querySelectorAll('.shortcut-card'));
  var empty = $('shortcuts-empty-state');

  function filter() {
    if (!input) return;
    var q = input.value.trim().toLowerCase(), shown = 0;
    cards.forEach(function (c) {
      var hay = (c.textContent + ' ' + (c.getAttribute('data-keywords') || '')).toLowerCase();
      var ok = !q || hay.indexOf(q) !== -1;
      c.classList.toggle('is-hidden', !ok);
      if (ok) shown++;
    });
    if (empty) empty.hidden = shown !== 0;
  }
  function clearFilter() {
    if (!input) return;
    input.value = ''; filter();
  }

  if (input) {
    input.addEventListener('input', function () {
      if (typeof stopRedirect === 'function') stopRedirect();
      filter();
    });
    input.addEventListener('focus', function () {
      if (typeof stopRedirect === 'function') stopRedirect();
    });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        var first = cards.filter(function (c) { return !c.classList.contains('is-hidden'); })[0];
        if (first) location.href = first.getAttribute('href');
      } else if (e.key === 'Escape') {
        clearFilter(); input.blur();
      }
    });
  }

  var clearBtn = $('clear-filter-btn');
  if (clearBtn && input) {
    clearBtn.addEventListener('click', function () { clearFilter(); input.focus(); });
  }

  document.addEventListener('keydown', function (e) {
    var tag = document.activeElement ? document.activeElement.tagName : '';
    if (e.key === '/' && tag !== 'INPUT' && tag !== 'TEXTAREA' && input) {
      e.preventDefault(); input.focus();
    }
  });

  if (reduceMotion) return;

  /* ---------- 3D card tilt (desktop only) ---------- */
  var stage = $('card-stage'), card = $('tilt-card');
  var canTilt = window.matchMedia && window.matchMedia('(hover: hover) and (min-width: 1025px)').matches;
  if (canTilt && stage && card) {
    stage.addEventListener('mousemove', function (e) {
      var r = stage.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - .5;
      var y = (e.clientY - r.top) / r.height - .5;
      card.style.transform = 'rotateY(' + (x * 14).toFixed(2) + 'deg) rotateX(' + (-y * 14).toFixed(2) + 'deg)';
    });
    stage.addEventListener('mouseleave', function () { card.style.transform = ''; });
  }

  /* ---------- Particle network ---------- */
  var cv = $('particle-canvas');
  if (!cv) return;
  var ctx = cv.getContext('2d');
  if (!ctx) return;
  var W, H, pts = [], mouse = { x: -999, y: -999 }, LINK = 130;

  function resize() {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth; H = window.innerHeight;
    cv.width = W * dpr; cv.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    var n = Math.min(80, Math.round(W * H / 18000));
    if (W < 700) n = Math.min(n, 28);
    pts = [];
    for (var i = 0; i < n; i++) {
      pts.push({ x: Math.random() * W, y: Math.random() * H, vx: (Math.random() - .5) * .4, vy: (Math.random() - .5) * .4, r: Math.random() * 1.5 + .6 });
    }
  }
  window.addEventListener('resize', resize);
  window.addEventListener('mousemove', function (e) { mouse.x = e.clientX; mouse.y = e.clientY; });
  resize();

  function frame() {
    var light = root.getAttribute('data-theme') === 'light';
    var dot = light ? '10,156,138' : '20,217,192';
    var line = light ? '47,90,230' : '59,108,255';
    ctx.clearRect(0, 0, W, H);

    for (var i = 0; i < pts.length; i++) {
      var p = pts[i];
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > W) p.vx *= -1;
      if (p.y < 0 || p.y > H) p.vy *= -1;

      var dx = p.x - mouse.x, dy = p.y - mouse.y, d = Math.sqrt(dx * dx + dy * dy);
      if (d < 120 && d > 0) { p.x += dx / d * .9; p.y += dy / d * .9; }

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, 6.2832);
      ctx.fillStyle = 'rgba(' + dot + ',.7)';
      ctx.fill();

      for (var j = i + 1; j < pts.length; j++) {
        var q = pts[j], ax = p.x - q.x, ay = p.y - q.y, dist = Math.sqrt(ax * ax + ay * ay);
        if (dist < LINK) {
          ctx.strokeStyle = 'rgba(' + line + ',' + (.22 * (1 - dist / LINK)).toFixed(3) + ')';
          ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke();
        }
      }
    }
    requestAnimationFrame(frame);
  }
  frame();
})();
