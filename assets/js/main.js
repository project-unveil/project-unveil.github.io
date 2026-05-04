/* ── Navbar: transparent → white on scroll ─────────────────── */
(function () {
  const nav = document.getElementById('main-nav');
  if (!nav) return;
  window.addEventListener('scroll', () => {
    if (window.scrollY > 40) {
      nav.classList.add('scrolled');
    } else {
      nav.classList.remove('scrolled');
    }
  }, { passive: true });
})();

/* ── Generic fade-in via IntersectionObserver ──────────────── */
(function () {
  const targets = document.querySelectorAll('.fade-in');
  if (!targets.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });

  targets.forEach(el => observer.observe(el));
})();

/* ── Teaser pipeline: staggered reveal ─────────────────────── */
(function () {
  const pipeline = document.querySelector('.teaser-pipeline');
  if (!pipeline) return;

  const nodes   = pipeline.querySelectorAll('.pipeline-node');
  const arrows  = pipeline.querySelectorAll('.pipeline-arrow');
  const allEls  = Array.from(pipeline.children);

  const observer = new IntersectionObserver((entries) => {
    if (!entries[0].isIntersecting) return;
    observer.disconnect();

    // Reveal elements in order with staggered delays
    allEls.forEach((el, i) => {
      setTimeout(() => {
        el.classList.add('visible');
      }, i * 260);
    });

    // After everything is visible, start counter animations
    const delay = allEls.length * 260 + 100;
    setTimeout(animateCounters, delay);
  }, { threshold: 0.25 });

  observer.observe(pipeline);
})();

/* ── Counter animation for numeric attr values ─────────────── */
function animateCounters() {
  document.querySelectorAll('[data-count-to]').forEach(el => {
    const target   = parseFloat(el.dataset.countTo);
    const decimals = el.dataset.decimals ? parseInt(el.dataset.decimals) : 0;
    const suffix   = el.dataset.suffix   || '';
    const duration = 900; // ms
    const start    = performance.now();

    function step(now) {
      const elapsed  = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased    = 1 - Math.pow(1 - progress, 3);
      const current  = target * eased;
      el.textContent = current.toFixed(decimals) + suffix;
      if (progress < 1) requestAnimationFrame(step);
    }

    requestAnimationFrame(step);
  });
}

/* ── Master sync controller (drives all 3 viewer iframes) ──── */
(function () {
  const btnPlay  = document.getElementById('sync-play');
  const progEl   = document.getElementById('sync-progress');
  const timeEl   = document.getElementById('sync-time');
  const speedSel = document.getElementById('sync-speed');
  if (!btnPlay) return;

  const IFRAMES = ['iframe-g1', 'iframe-predicted', 'iframe-groundtruth'];
  const SEQ_DURATION = 3303 / 120;  // 27.5s — macarena dance (G1: 3303 frames @ 120fps)
  let   masterTime = 0;
  let   playing    = false;
  let   lastTS     = null;
  let   speed      = 1;

  function getIframes() {
    return IFRAMES.map(id => document.getElementById(id))
                  .filter(Boolean)
                  .map(el => el.contentWindow)
                  .filter(Boolean);
  }

  function broadcast() {
    const msg = { type: 'SYNC', time: masterTime, playing, speed };
    getIframes().forEach(w => w.postMessage(msg, '*'));
  }

  function setPlaying(val) {
    playing = val;
    btnPlay.innerHTML = playing ? '&#9646;&#9646;' : '&#9654;';
    if (playing) lastTS = null;
    broadcast();
  }

  btnPlay.addEventListener('click', () => setPlaying(!playing));

  progEl.addEventListener('input', () => {
    masterTime = parseFloat(progEl.value) * SEQ_DURATION;
    broadcast();
  });

  speedSel.addEventListener('change', () => {
    speed = parseFloat(speedSel.value);
    broadcast();
  });

  function tick(ts) {
    requestAnimationFrame(tick);
    if (playing) {
      if (lastTS === null) lastTS = ts;
      const dt = (ts - lastTS) * 0.001 * speed;
      lastTS = ts;
      masterTime += dt;
      if (masterTime >= SEQ_DURATION) masterTime %= SEQ_DURATION;
    } else {
      lastTS = null;
    }

    broadcast();

    const frac = masterTime / SEQ_DURATION;
    progEl.value = frac;
    timeEl.textContent = masterTime.toFixed(2) + ' / ' + SEQ_DURATION.toFixed(2) + 's';
  }

  // Start paused; auto-play once at least one iframe loads
  window.addEventListener('message', e => {
    if (e.data && e.data.type === 'READY' && !playing) setPlaying(true);
  });

  requestAnimationFrame(tick);
})();

/* ── Demo panel fade-in with staggered delay ───────────────── */
(function () {
  const panels = document.querySelectorAll('.demo-panel[data-delay]');
  if (!panels.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el    = entry.target;
      const delay = parseInt(el.dataset.delay || 0);
      setTimeout(() => el.classList.add('visible'), delay);
      observer.unobserve(el);
    });
  }, { threshold: 0.15 });

  panels.forEach(p => observer.observe(p));
})();

/* ── Predicted attribute color-coding (error → green…red) ─── */
(function () {
  // Green color scale: 0=perfect (vivid) → 2×MAE (muted sage)
  function errorChipColors(pred, gt, mae) {
    const ratio = Math.abs(pred - gt) / mae;
    const t     = Math.min(ratio / 2, 1);   // 0=perfect, 1=2×MAE
    const hue   = 130;
    // Box background: bright green → pale sage
    const bgSat = Math.round(60 - 44 * t);
    const bgLig = Math.round(91 +  4 * t);
    // Box border: visible but not loud
    const bdSat = Math.round(52 - 36 * t);
    const bdLig = Math.round(62 + 14 * t);
    // Value text: rich green → muted
    const txSat = Math.round(70 - 40 * t);
    const txLig = Math.round(34 + 10 * t);
    return {
      bg:     `hsl(${hue}, ${bgSat}%, ${bgLig}%)`,
      border: `hsl(${hue}, ${bdSat}%, ${bdLig}%)`,
      color:  `hsl(${hue}, ${txSat}%, ${txLig}%)`,
    };
  }

  function applyColors() {
    document.querySelectorAll('.attr-chip[data-pred]').forEach(chip => {
      const pred  = parseFloat(chip.dataset.pred);
      const gt    = parseFloat(chip.dataset.gt);
      const mae   = parseFloat(chip.dataset.mae);
      const c     = errorChipColors(pred, gt, mae);
      chip.style.background   = c.bg;
      chip.style.borderColor  = c.border;
      const valEl = chip.querySelector('.attr-chip-value');
      if (valEl) valEl.style.color = c.color;
    });
  }

  // Run once DOM is ready, and again on scroll (fade-in may delay visibility)
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyColors);
  } else {
    applyColors();
  }
})();

/* ── PDF.js: render PDF figures to canvas ──────────────────── */
(function () {
  const canvases = document.querySelectorAll('canvas[data-pdf]');
  if (!canvases.length) return;

  const pdfjsLib = window['pdfjs-dist/build/pdf'];
  if (!pdfjsLib) { console.warn('PDF.js not loaded'); return; }

  pdfjsLib.GlobalWorkerOptions.workerSrc =
    'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

  canvases.forEach(async (canvas) => {
    try {
      const pdf      = await pdfjsLib.getDocument(canvas.dataset.pdf).promise;
      const page     = await pdf.getPage(1);
      const dpr      = window.devicePixelRatio || 1;
      const contW    = canvas.parentElement.offsetWidth || 900;
      const baseVp   = page.getViewport({ scale: 1 });
      const scale    = (contW / baseVp.width) * dpr;
      const viewport = page.getViewport({ scale });

      canvas.width  = viewport.width;
      canvas.height = viewport.height;

      await page.render({
        canvasContext: canvas.getContext('2d'),
        viewport,
      }).promise;

      canvas.classList.add('rendered');
    } catch (err) {
      console.error('PDF render error:', canvas.dataset.pdf, err);
    }
  });
})();

/* ── Smooth close of mobile nav on link click ──────────────── */
(function () {
  const toggler    = document.querySelector('.navbar-toggler');
  const navCollapse = document.getElementById('navbarLinks');
  if (!navCollapse) return;

  document.querySelectorAll('#navbarLinks .nav-link').forEach(link => {
    link.addEventListener('click', () => {
      if (navCollapse.classList.contains('show')) {
        toggler && toggler.click();
      }
    });
  });
})();
