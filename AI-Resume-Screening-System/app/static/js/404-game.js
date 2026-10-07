/* static/js/404-game.js | Catch the Candidate */
(function () {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };
  if (!$('game-panel') || !$('game-playfield') || !$('game-start-btn')) return;

  var el = {
    start: $('game-screen-start'), play: $('game-screen-play'), over: $('game-screen-over'),
    field: $('game-playfield'), overlay: $('game-overlay'), big: $('game-overlay-big'),
    sub: $('game-overlay-sub'), resume: $('game-resume-btn'), pause: $('game-pause-btn'),
    btnStart: $('game-start-btn'), btnRestart: $('game-restart-btn'),
    time: $('game-time-val'), timeStat: $('game-time-stat'), score: $('game-score-val'),
    combo: $('game-combo-val'), streak: $('game-streak-val'), hudBest: $('game-hud-best'),
    bar: $('game-bar-fill'), startBest: $('game-start-best'),
    finalScore: $('game-final-score'), bestScore: $('game-best-score'),
    newBest: $('game-new-best'), rank: $('game-rank'), status: $('game-sr-status')
  };

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var CFG = { time: 30, ready: 3, golden: 1 / 12, good: 0.72, comboAt: 3, slow: 2, slowFactor: 0.45 };
  var GOOD = ['Python', 'React', 'ML Engineer', 'Flask', 'SQL', 'TypeScript', 'Node.js', 'PyTorch', 'Data Scientist'];
  var BAD = ['Spam CV', 'Fake Bot', 'Scammer', 'Keyword Stuffer'];
  var RANKS = [[0, 'Intern'], [60, 'Junior Recruiter'], [130, 'Talent Scout'], [230, 'Head Hunter'], [350, 'Chief Talent Officer']];

  var phase = 'idle';              // idle | ready | play | paused | over
  var rafId = 0, lastTs = 0;
  var timeLeft, readyLeft, spawnIn, slowLeft, score, streak, best = 0;
  var cards = [], shownSecs = -1, shownReady = -1;

  try { best = parseInt(localStorage.getItem('ts-404-best'), 10) || 0; } catch (e) {}

  function say(msg) { if (el.status) el.status.textContent = msg; }
  function show(node, on) { if (node) node.hidden = !on; }
  function screen(name) { show(el.start, name === 'start'); show(el.play, name === 'play'); show(el.over, name === 'over'); }
  function rnd(a, b) { return a + Math.random() * (b - a); }

  function renderBest() {
    if (el.hudBest) el.hudBest.textContent = Math.max(best, score || 0);
    if (el.startBest) { el.startBest.hidden = !best; el.startBest.textContent = 'Your best: ' + best; }
  }

  function renderHud() {
    var mult = streak >= CFG.comboAt ? 2 : 1;
    el.score.textContent = score;
    el.combo.textContent = mult > 1 ? 'x2 🔥' : 'x1';
    el.streak.textContent = mult > 1 ? streak + ' in a row' : streak + '/' + CFG.comboAt;
    renderBest();
  }

  function renderTime() {
    var secs = Math.ceil(timeLeft);
    if (secs !== shownSecs) {
      shownSecs = secs;
      el.time.textContent = secs + 's';
      var low = secs <= 5;
      el.timeStat.classList.toggle('is-low', low);
      el.bar.classList.toggle('is-low', low);
    }
    el.bar.style.transform = 'scaleX(' + (timeLeft / CFG.time).toFixed(4) + ')';
  }

  function overlay(big, withResume) {
    el.big.textContent = big;
    el.big.classList.remove('tick');
    void el.big.offsetWidth;
    if (!withResume) el.big.classList.add('tick');
    show(el.resume, withResume); show(el.sub, withResume); show(el.overlay, true);
  }

  /* ---------- Spawning ---------- */
  function tier() { return Math.floor((CFG.time - timeLeft) / 10); }
  function nextInterval() { return Math.max(0.38, 0.85 - tier() * 0.14) * rnd(0.85, 1.15); }

  function spawn() {
    var r = Math.random();
    var type = r < CFG.golden ? 'golden' : (Math.random() < CFG.good ? 'good' : 'bad');
    var node = document.createElement('div');
    node.className = 'game-card ' + type;
    var label = type === 'golden' ? 'Golden Lead' : (type === 'good' ? GOOD : BAD)[Math.floor(Math.random() * (type === 'good' ? GOOD : BAD).length)];
    node.innerHTML = '<div class="game-card-body"><span class="game-avatar" aria-hidden="true">' +
      (type === 'golden' ? '⭐' : type === 'good' ? '👤' : '⚠️') + '</span><span class="game-tag"></span></div>';
    node.querySelector('.game-tag').textContent = label;
    el.field.appendChild(node);

    var w = node.offsetWidth, h = node.offsetHeight;
    var c = {
      el: node, type: type, w: w, h: h, caught: false,
      x: rnd(8, Math.max(9, el.field.clientWidth - w - 8)),
      y: el.field.clientHeight + 10,
      speed: reduce ? 130 : 105 + tier() * 30 + rnd(0, 45)
    };
    node.style.transform = 'translate3d(' + c.x + 'px,' + c.y + 'px,0)';
    node.addEventListener('pointerdown', function (e) { e.preventDefault(); catchCard(c); });
    cards.push(c);
  }

  function popup(x, y, text, kind) {
    var p = document.createElement('div');
    p.className = 'game-popup ' + kind;
    p.textContent = text;
    p.style.left = x + 'px'; p.style.top = Math.max(10, y) + 'px';
    el.field.appendChild(p);
    setTimeout(function () { if (p.parentNode) p.parentNode.removeChild(p); }, 750);
  }

  /* ---------- Scoring ---------- */
  function catchCard(c) {
    if (phase !== 'play' || c.caught) return;
    c.caught = true;
    c.el.classList.add('caught');
    setTimeout(function () { if (c.el.parentNode) c.el.parentNode.removeChild(c.el); }, 240);

    var mult = streak >= CFG.comboAt ? 2 : 1, pts, kind, text;
    if (c.type === 'bad') {
      pts = -15; kind = 'bad'; text = '-15'; streak = 0;
      if (!reduce) { el.field.classList.remove('is-shake'); void el.field.offsetWidth; el.field.classList.add('is-shake'); }
    } else {
      pts = (c.type === 'golden' ? 50 : 10) * mult; kind = c.type;
      text = '+' + pts + (c.type === 'golden' ? ' ⭐' : '');
      streak += 1;
      if (streak === CFG.comboAt) say('Combo x2 active');
      if (c.type === 'golden' && !reduce) { slowLeft = CFG.slow; el.field.classList.add('is-slow'); }
    }
    score = Math.max(0, score + pts);
    popup(c.x + c.w / 2, c.y, text, kind);
    renderHud();
  }

  /* ---------- Main loop (time-based, same speed on 60Hz and 144Hz) ---------- */
  function loop(now) {
    rafId = requestAnimationFrame(loop);
    var dt = Math.min((now - lastTs) / 1000, 0.05);
    lastTs = now;

    if (phase === 'ready') {
      readyLeft -= dt;
      var n = Math.ceil(readyLeft);
      if (readyLeft <= 0) { phase = 'play'; show(el.overlay, false); say('Go'); el.field.focus({ preventScroll: true }); }
      else if (n !== shownReady) { shownReady = n; overlay(String(n), false); }
      return;
    }
    if (phase !== 'play') return;

    timeLeft -= dt;
    if (timeLeft <= 0) { timeLeft = 0; renderTime(); endRound(); return; }

    if (slowLeft > 0) { slowLeft -= dt; if (slowLeft <= 0) el.field.classList.remove('is-slow'); }
    var f = slowLeft > 0 ? CFG.slowFactor : 1;

    spawnIn -= dt;
    if (spawnIn <= 0) { spawn(); spawnIn = nextInterval(); }

    for (var i = cards.length - 1; i >= 0; i--) {
      var c = cards[i];
      if (c.caught) { cards.splice(i, 1); continue; }
      c.y -= c.speed * f * dt;
      c.el.style.transform = 'translate3d(' + c.x + 'px,' + c.y + 'px,0)';
      if (c.y < -c.h - 10) {
        if (c.type !== 'bad' && streak) { streak = 0; renderHud(); }
        if (c.el.parentNode) c.el.parentNode.removeChild(c.el);
        cards.splice(i, 1);
      }
    }
    renderTime();
  }

  function runLoop() { cancelAnimationFrame(rafId); lastTs = performance.now(); rafId = requestAnimationFrame(loop); }

  /* ---------- Flow ---------- */
  function startRound() {
    var cancel = $('cancel-redirect-btn');          // stop the 404 auto-redirect
    if (cancel) cancel.click();

    el.field.innerHTML = '';
    el.field.classList.remove('is-slow', 'is-shake');
    cards = []; score = 0; streak = 0; slowLeft = 0; spawnIn = 0.4;
    timeLeft = CFG.time; readyLeft = CFG.ready; shownSecs = -1; shownReady = -1;
    el.timeStat.classList.remove('is-low'); el.bar.classList.remove('is-low');

    renderHud(); renderTime();
    screen('play');
    phase = 'ready';
    overlay(String(CFG.ready), false);
    say('Round starting');
    el.field.focus({ preventScroll: true });
    runLoop();
  }

  function endRound() {
    phase = 'over';
    cancelAnimationFrame(rafId);
    show(el.overlay, false);
    var isBest = score > best;
    if (isBest) { best = score; try { localStorage.setItem('ts-404-best', String(best)); } catch (e) {} }
    var rank = RANKS[0][1];
    RANKS.forEach(function (r) { if (score >= r[0]) rank = r[1]; });
    el.finalScore.textContent = score;
    el.bestScore.textContent = best;
    el.rank.textContent = 'Rank: ' + rank;
    show(el.newBest, isBest);
    renderBest();
    screen('over');
    say('Round finished. Score ' + score + '. Rank ' + rank + '.');
    el.btnRestart.focus({ preventScroll: true });
  }

  function pause() {
    if (phase !== 'play') return;
    phase = 'paused';
    cancelAnimationFrame(rafId);
    overlay('Paused', true);
    el.resume.focus({ preventScroll: true });
  }

  function resume() {
    if (phase !== 'paused') return;
    phase = 'play';
    show(el.overlay, false);
    el.field.focus({ preventScroll: true });
    runLoop();
  }

  /* ---------- Events ---------- */
  el.btnStart.addEventListener('click', startRound);
  el.btnRestart.addEventListener('click', startRound);
  el.resume.addEventListener('click', resume);
  el.pause.addEventListener('click', function () { phase === 'paused' ? resume() : pause(); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { if (phase === 'play') pause(); else if (phase === 'paused') resume(); }
  });
  document.addEventListener('visibilitychange', function () { if (document.hidden) pause(); });

  renderBest();
})();
