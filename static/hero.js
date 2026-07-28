(function () {
  var hero = document.getElementById('hero-premium');
  if (!hero) return;

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduceMotion) return;

  var ambientEl = hero.querySelector('.hero-ambient');
  var glowEl = hero.querySelector('.hero-image-glow');
  var tiltEl = hero.querySelector('.hero-image-tilt');

  var raf = null;
  var mouse = { x: 50, y: 30, nx: 0, ny: 0 };
  var scrollOffset = 0;

  function render() {
    raf = null;
    hero.style.setProperty('--mx', mouse.x + '%');
    hero.style.setProperty('--my', mouse.y + '%');
    if (ambientEl) {
      ambientEl.style.transform =
        'translate3d(' + (mouse.nx * 14) + 'px,' + (mouse.ny * 10 + scrollOffset) + 'px,0)';
    }
    if (glowEl) {
      glowEl.style.transform = 'translate3d(' + (mouse.nx * -10) + 'px,' + (mouse.ny * -8) + 'px,0)';
    }
  }

  function schedule() {
    if (!raf) raf = requestAnimationFrame(render);
  }

  hero.addEventListener('mousemove', function (e) {
    var rect = hero.getBoundingClientRect();
    mouse.x = ((e.clientX - rect.left) / rect.width) * 100;
    mouse.y = ((e.clientY - rect.top) / rect.height) * 100;
    mouse.nx = (e.clientX - rect.left - rect.width / 2) / (rect.width / 2);
    mouse.ny = (e.clientY - rect.top - rect.height / 2) / (rect.height / 2);
    schedule();
  });

  hero.addEventListener('mouseleave', function () {
    mouse.x = 50; mouse.y = 30; mouse.nx = 0; mouse.ny = 0;
    schedule();
  });

  window.addEventListener('scroll', function () {
    var rect = hero.getBoundingClientRect();
    if (rect.bottom < 0 || rect.top > window.innerHeight) return;
    scrollOffset = Math.max(-24, Math.min(24, rect.top * -0.04));
    schedule();
  }, { passive: true });

  if (tiltEl) {
    tiltEl.addEventListener('mousemove', function (e) {
      var rect = tiltEl.getBoundingClientRect();
      var px = (e.clientX - rect.left) / rect.width - 0.5;
      var py = (e.clientY - rect.top) / rect.height - 0.5;
      tiltEl.style.setProperty('--ry', (px * 8) + 'deg');
      tiltEl.style.setProperty('--rx', (py * -8) + 'deg');
    });
    tiltEl.addEventListener('mouseleave', function () {
      tiltEl.style.setProperty('--ry', '0deg');
      tiltEl.style.setProperty('--rx', '0deg');
    });
  }

  var magnets = hero.querySelectorAll('.magnetic');
  magnets.forEach(function (el) {
    var strength = parseFloat(el.dataset.magneticStrength || '0.3');
    el.addEventListener('mousemove', function (e) {
      var rect = el.getBoundingClientRect();
      var mx = (e.clientX - rect.left - rect.width / 2) * strength;
      var my = (e.clientY - rect.top - rect.height / 2) * strength;
      el.style.setProperty('--tx', mx + 'px');
      el.style.setProperty('--ty', my + 'px');
    });
    el.addEventListener('mouseleave', function () {
      el.style.setProperty('--tx', '0px');
      el.style.setProperty('--ty', '0px');
    });
  });

  // Scroll reveal for the rest of the home page (testimonials, categories,
  // feature blocks, stats). CSS keeps everything visible until html.js-reveal
  // is set AND the user allows motion, so this is a pure enhancement.
  var revealEls = document.querySelectorAll('.reveal');
  if (revealEls.length) {
    if ('IntersectionObserver' in window) {
      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
      revealEls.forEach(function (el) { observer.observe(el); });
    } else {
      revealEls.forEach(function (el) { el.classList.add('is-visible'); });
    }
  }
})();
