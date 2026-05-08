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

/* ── Activity demo selector ────────────────────────────────── */
(function () {
  const sel    = document.getElementById('activity-select');
  const countEl= document.getElementById('activity-count');
  if (!sel) return;

  let demosConfig = null;

  function getIframes() {
    return ['iframe-g1','iframe-predicted','iframe-groundtruth']
      .map(id => document.getElementById(id))
      .filter(Boolean);
  }

  function sendDemo(demo) {
    const iframes = getIframes();
    iframes.forEach(ifr => ifr.closest('.demo-panel')?.classList.add('loading'));

    // Update attribute chips
    updateChips(demo);

    // Update sync duration
    if (typeof SEQ_DURATION !== 'undefined') {
      // handled in sync controller below
    }

    // Dispatch to all viewers
    iframes.forEach(ifr => {
      ifr.contentWindow?.postMessage({ type: 'LOAD_DEMO', demo }, '*');
    });

    // Remove loading state after a short delay
    setTimeout(() => {
      iframes.forEach(ifr => ifr.closest('.demo-panel')?.classList.remove('loading'));
    }, 3500);
  }

  function updateChips(demo) {
    // Update predicted chips
    const predChips = document.querySelectorAll('.attr-chip[data-pred]');
    const p = demo.predicted, g = demo.groundTruth;
    const fields = [
      { label:'Height', predVal: p.height + ' cm', gtVal: g.height + ' cm',
        pred: p.height, gt: g.height, mae: 4.4 },
      { label:'Weight', predVal: p.weight + ' kg', gtVal: g.weight + ' kg',
        pred: p.weight, gt: g.weight, mae: 8.9 },
      { label:'Age',    predVal: p.age    + ' yrs', gtVal: g.age    + ' yrs',
        pred: p.age,    gt: g.age,    mae: 4.07 },
      { label:'Gender', predVal: p.gender.charAt(0).toUpperCase()+p.gender.slice(1),
        gtVal: g.gender.charAt(0).toUpperCase()+g.gender.slice(1),
        pred: 1, gt: 1, mae: 1 },
    ];
    predChips.forEach((chip, i) => {
      if (!fields[i]) return;
      const f = fields[i];
      chip.dataset.pred = f.pred;
      chip.dataset.gt   = f.gt;
      chip.dataset.mae  = f.mae;
      chip.querySelector('.attr-chip-value').textContent = f.predVal;
    });

    // Update GT chips
    document.querySelectorAll('.attr-chip--gt').forEach((chip, i) => {
      if (!fields[i]) return;
      chip.querySelector('.attr-chip-value').textContent = fields[i].gtVal;
    });

    // Re-apply color coding
    applyDemoColors(fields);
  }

  function applyDemoColors(fields) {
    function errorChipColors(pred, gt, mae) {
      const ratio = Math.abs(pred - gt) / mae;
      const t     = Math.min(ratio / 2, 1);
      const hue   = 130;
      return {
        bg:    `hsl(${hue}, ${Math.round(60-44*t)}%, ${Math.round(91+4*t)}%)`,
        border:`hsl(${hue}, ${Math.round(52-36*t)}%, ${Math.round(62+14*t)}%)`,
        color: `hsl(${hue}, ${Math.round(70-40*t)}%, ${Math.round(34+10*t)}%)`,
      };
    }
    document.querySelectorAll('.attr-chip[data-pred]').forEach(chip => {
      const c = errorChipColors(+chip.dataset.pred, +chip.dataset.gt, +chip.dataset.mae);
      chip.style.background  = c.bg;
      chip.style.borderColor = c.border;
      const v = chip.querySelector('.attr-chip-value');
      if (v) v.style.color = c.color;
    });
  }

  // Preload top N demos silently after page is idle
  function preloadDemosInBackground(cfg, topN = 4) {
    const toPreload = cfg.demos.slice(0, topN);   // already sorted by count desc
    const iframes   = getIframes();
    let   idx       = 0;

    function next() {
      if (idx >= toPreload.length) return;
      const demo = toPreload[idx++];
      // Send a silent preload hint to each SMPL iframe
      iframes.forEach(ifr => {
        ifr.contentWindow?.postMessage({ type: 'PRELOAD_DEMO', demo }, '*');
      });
      // Stagger to avoid saturating bandwidth
      setTimeout(next, 4000);
    }
    setTimeout(next, 5000);   // start 5s after page load
  }

  async function init() {
    try {
      const cfg = await fetch('./assets/demos/demos_config.json').then(r => r.json());
      demosConfig = cfg;

      sel.innerHTML = '';
      cfg.demos.forEach(demo => {
        const opt = document.createElement('option');
        opt.value = demo.id;
        opt.textContent = demo.label;
        if (demo.id === cfg.defaultDemo) opt.selected = true;
        sel.appendChild(opt);
      });

      // Show count for default
      const def = cfg.demos.find(d => d.id === cfg.defaultDemo);
      if (def && countEl) countEl.textContent = def.count.toLocaleString() + ' clips';

      // Preload top demos silently after page settles
      preloadDemosInBackground(cfg);

    } catch(e) {
      console.warn('demos_config not ready yet:', e.message);
      sel.innerHTML = '<option value="dancing">Dancing (default)</option>';
    }
  }

  sel.addEventListener('change', () => {
    if (!demosConfig) return;
    const demo = demosConfig.demos.find(d => d.id === sel.value);
    if (!demo) return;
    sendDemo(demo);
    // Update sync duration
    window._demoDuration = demo.numFrames / demo.fps;
  });

  init();
  window.getDemosConfig = () => demosConfig;
})();

/* ── Master sync controller (drives all 3 viewer iframes) ──── */
(function () {
  const btnPlay  = document.getElementById('sync-play');
  const progEl   = document.getElementById('sync-progress');
  const timeEl   = document.getElementById('sync-time');
  const speedSel = document.getElementById('sync-speed');
  if (!btnPlay) return;

  const IFRAMES = ['iframe-g1', 'iframe-predicted', 'iframe-groundtruth'];
  let   SEQ_DURATION = window._demoDuration || (3303 / 120);
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
    // Sync duration may update when demo changes
    if (window._demoDuration) { SEQ_DURATION = window._demoDuration; window._demoDuration = null; }
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
  function renderPDFs() {
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
  }

  // Defer until after layout so offsetWidth is reliable
  if (document.readyState === 'complete') {
    renderPDFs();
  } else {
    window.addEventListener('load', renderPDFs);
  }
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
