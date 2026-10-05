// GoSki website: light decoration only (snowfall, the ski track, reveals, the resort marquee).
// The page reads fine without any of it.
(() => {
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');

  // Nav gets a frosted bar once the page scrolls.
  const nav = document.querySelector('[data-nav]');
  const onScrollNav = () => nav && nav.classList.toggle('is-scrolled', scrollY > 8);
  addEventListener('scroll', onScrollNav, { passive: true });
  onScrollNav();

  // Reveal blocks as they come into view; siblings follow each other a beat apart.
  const reveals = [...document.querySelectorAll('[data-reveal]')];
  for (const el of reveals) {
    const siblings = [...el.parentElement.children].filter(child => child.hasAttribute('data-reveal'));
    if (siblings.length > 1) el.style.setProperty('--d', `${siblings.indexOf(el) * 0.09}s`);
  }
  if ('IntersectionObserver' in window && !reduceMotion.matches) {
    const io = new IntersectionObserver(entries => {
      for (const entry of entries) if (entry.isIntersecting) { entry.target.classList.add('is-in'); io.unobserve(entry.target); }
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });
    reveals.forEach(el => io.observe(el));
  } else {
    reveals.forEach(el => el.classList.add('is-in'));
  }

  // Resort names loop: a second copy of the row makes the scroll seamless.
  const row = document.querySelector('[data-marquee] .marquee__row');
  if (row && !reduceMotion.matches) {
    for (const item of [...row.children]) {
      const copy = item.cloneNode(true);
      copy.setAttribute('aria-hidden', 'true');
      row.appendChild(copy);
    }
  }

  // Snowfall in the hero sky. Pauses when the hero is off screen or the tab is hidden.
  const canvas = document.querySelector('[data-snow]');
  if (canvas && canvas.getContext) {
    const ctx = canvas.getContext('2d');
    let w = 0, h = 0, flakes = [], raf = 0, last = 0, onScreen = true;
    const flake = anywhere => {
      const z = Math.random();
      return { x: Math.random() * w, y: anywhere ? Math.random() * h : -8 - Math.random() * 40,
        r: 0.7 + z * z * 2.6, v: 12 + z * 44, a: 0.18 + z * 0.5, p: Math.random() * 6.28, s: 0.4 + Math.random() * 0.9 };
    };
    const size = () => {
      const dpr = Math.min(devicePixelRatio || 1, 2);
      w = canvas.clientWidth; h = canvas.clientHeight;
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.round(Math.min(130, (w * h) / 10500));
      flakes = Array.from({ length: count }, () => flake(true));
    };
    // One soft flake, drawn once and stamped at each flake's size.
    const sprite = document.createElement('canvas');
    sprite.width = sprite.height = 32;
    const sctx = sprite.getContext('2d');
    const soft = sctx.createRadialGradient(16, 16, 0, 16, 16, 16);
    soft.addColorStop(0, 'rgba(255,255,255,1)');
    soft.addColorStop(0.35, 'rgba(255,255,255,.85)');
    soft.addColorStop(1, 'rgba(255,255,255,0)');
    sctx.fillStyle = soft;
    sctx.fillRect(0, 0, 32, 32);
    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      for (const f of flakes) {
        ctx.globalAlpha = f.a;
        const s = f.r * 3.2;
        ctx.drawImage(sprite, f.x - s / 2, f.y - s / 2, s, s);
      }
      ctx.globalAlpha = 1;
    };
    const step = now => {
      const dt = Math.min(0.05, (now - (last || now)) / 1000); last = now;
      for (const f of flakes) {
        f.p += dt * f.s;
        f.y += f.v * dt;
        f.x += (Math.sin(f.p) * 14 + 6) * dt;
        if (f.y > h + 8 || f.x > w + 8) Object.assign(f, flake(false));
      }
      draw();
      raf = requestAnimationFrame(step);
    };
    const start = () => { if (!raf && onScreen && !document.hidden && !reduceMotion.matches) { last = 0; raf = requestAnimationFrame(step); } };
    const stop = () => { cancelAnimationFrame(raf); raf = 0; };
    size(); draw();
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(([entry]) => { onScreen = entry.isIntersecting; onScreen ? start() : stop(); }).observe(canvas);
    }
    document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));
    let resizeTimer = 0;
    addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { size(); draw(); }, 150); });
    start();
  }

  // The ski track: one line carved down the page, through each chapter's phones, ending at the
  // app icon. The blue dot follows your scroll position, like the dot on the app icon.
  const track = document.querySelector('[data-track]');
  const main = document.getElementById('main');
  if (track && main && track.querySelector('path').getTotalLength) {
    const wide = matchMedia('(min-width: 1100px)');
    const line = track.querySelector('.track__line');
    const groove = track.querySelector('.track__groove');
    const dot = track.querySelector('.track__dot');
    const glow = track.querySelector('.track__glow');
    let samples = [], total = 0, ticking = false;

    const centerOf = (el, origin) => {
      const r = el.getBoundingClientRect();
      return [r.left + r.width / 2 - origin.left, r.top + r.height / 2 - origin.top];
    };
    const build = () => {
      if (!wide.matches) { track.classList.remove('is-ready'); samples = []; return; }
      const origin = main.getBoundingClientRect();
      const width = main.clientWidth, height = main.scrollHeight;
      track.setAttribute('viewBox', `0 0 ${width} ${height}`);
      track.style.height = `${height}px`;

      const start = document.querySelector('.hero__dot');
      const anchors = [...document.querySelectorAll('[data-track-anchor]')];
      const end = document.querySelector('.finale__icon');
      const more = document.querySelector('.more');
      if (!start || !end || !anchors.length || !more) return;

      const points = [centerOf(start, origin), ...anchors.map(a => centerOf(a, origin))];
      // After the last chapter the track runs down the left margin, clear of the text,
      // then swings across to the icon.
      const content = document.querySelector('.more__inner').getBoundingClientRect();
      const margin = Math.max(18, (content.left - origin.left) * 0.55);
      const moreTop = more.getBoundingClientRect().top - origin.top;
      const finaleTop = document.querySelector('.finale').getBoundingClientRect().top - origin.top;
      points.push([margin, moreTop + 40], [margin, finaleTop + 10]);
      // Finish on the blue dot in the app icon's artwork.
      const icon = end.getBoundingClientRect();
      points.push([icon.left + icon.width * 0.72 - origin.left, icon.top + icon.height * 0.79 - origin.top]);

      let d = `M${points[0][0].toFixed(1)} ${points[0][1].toFixed(1)}`;
      for (let i = 1; i < points.length; i++) {
        const [x0, y0] = points[i - 1], [x1, y1] = points[i], k = (y1 - y0) * 0.5;
        d += ` C${x0.toFixed(1)} ${(y0 + k).toFixed(1)} ${x1.toFixed(1)} ${(y1 - k).toFixed(1)} ${x1.toFixed(1)} ${y1.toFixed(1)}`;
      }
      line.setAttribute('d', d);
      groove.setAttribute('d', d);
      total = line.getTotalLength();
      line.style.strokeDasharray = `${total} ${total}`;
      samples = [];
      const n = 700;
      for (let i = 0; i <= n; i++) {
        const length = (total * i) / n, p = line.getPointAtLength(length);
        samples.push({ length, x: p.x, y: p.y });
      }
      track.classList.add('is-ready');
      update();
    };
    const update = () => {
      ticking = false;
      if (!samples.length) return;
      let s = samples[samples.length - 1];
      if (!reduceMotion.matches) {
        const target = scrollY + innerHeight * 0.58 - (main.getBoundingClientRect().top + scrollY);
        let lo = 0, hi = samples.length - 1;
        while (lo < hi) { const mid = (lo + hi) >> 1; if (samples[mid].y < target) lo = mid + 1; else hi = mid; }
        s = samples[lo];
      }
      line.style.strokeDashoffset = `${total - s.length}`;
      const atStart = s.length < 2, atEnd = s.length > total - 2;
      dot.setAttribute('cx', s.x); dot.setAttribute('cy', s.y);
      glow.setAttribute('cx', s.x); glow.setAttribute('cy', s.y);
      // At the finish the icon's own dot takes over; only the glow stays.
      dot.style.opacity = atStart || atEnd ? '0' : '1';
      glow.style.opacity = atStart ? '0' : '1';
    };
    addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
    let buildTimer = 0;
    const rebuild = () => { clearTimeout(buildTimer); buildTimer = setTimeout(build, 120); };
    addEventListener('resize', rebuild);
    addEventListener('load', rebuild);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(rebuild);
    wide.addEventListener?.('change', rebuild);
    rebuild();
  }
})();
