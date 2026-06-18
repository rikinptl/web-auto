(() => {
  "use strict";

  document.documentElement.classList.add("js-ready");
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const header = document.querySelector("[data-header]");
  const navToggle = document.querySelector("[data-nav-toggle]");
  const navMobile = document.querySelector("[data-nav-mobile]");
  const progress = document.querySelector(".scroll-progress");
  const parallaxEls = [...document.querySelectorAll("[data-parallax]")];

  let parallaxTicking = false;

  function setNavOpen(isOpen) {
    document.body.classList.toggle("nav-open", isOpen);
    if (navToggle) {
      navToggle.setAttribute("aria-expanded", String(isOpen));
      navToggle.setAttribute("aria-label", isOpen ? "Close menu" : "Open menu");
    }
    if (navMobile) {
      if (isOpen) navMobile.removeAttribute("hidden");
      else navMobile.setAttribute("hidden", "");
    }
  }

  function updateParallax() {
    parallaxTicking = false;
    if (reduced || !parallaxEls.length) return;

    const scrollY = window.scrollY;
    const viewMid = window.innerHeight * 0.5;

    parallaxEls.forEach((el) => {
      const speed = parseFloat(el.getAttribute("data-parallax") || "0");
      const rect = el.getBoundingClientRect();
      const elMid = rect.top + rect.height * 0.5;
      const offset = (elMid - viewMid) * speed;
      el.style.transform = `translate3d(0, ${offset}px, 0)`;
    });
  }

  function requestParallax() {
    if (parallaxTicking || reduced) return;
    parallaxTicking = true;
    requestAnimationFrame(updateParallax);
  }

  function onScroll() {
    header?.classList.toggle("is-scrolled", window.scrollY > 24);
    if (progress) {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      progress.style.width = max > 0 ? `${(window.scrollY / max) * 100}%` : "0%";
    }
    requestParallax();
  }

  function isNearPageBottom() {
    return window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 120;
  }

  function scrollToTop() {
    window.scrollTo({ top: 0, behavior: reduced ? "auto" : "smooth" });
  }

  navToggle?.addEventListener("click", () => {
    if (isNearPageBottom()) {
      setNavOpen(false);
      scrollToTop();
      return;
    }

    const open = navMobile?.hasAttribute("hidden");
    setNavOpen(Boolean(open));
  });

  navMobile?.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => setNavOpen(false));
  });

  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  window.addEventListener("resize", () => {
    if (window.innerWidth > 768 && navMobile && !navMobile.hasAttribute("hidden")) {
      setNavOpen(false);
    }
    requestParallax();
  });

  /* Reveal delays */
  document.querySelectorAll("[data-reveal-delay]").forEach((el) => {
    const step = Number(el.getAttribute("data-reveal-delay") || 0);
    el.style.setProperty("--reveal-delay", String(step * 100));
  });

  document.querySelectorAll("[data-stagger]").forEach((grid) => {
    const step = Number(grid.getAttribute("data-stagger") || 80);
    grid.querySelectorAll(".reveal").forEach((el, i) => {
      el.style.setProperty("--reveal-delay", String(i * step));
    });
  });

  function reveal(el) {
    el.classList.add("is-visible");
  }

  /* Hero entrance on load */
  const heroItems = document.querySelectorAll(".hero-inner .reveal");
  heroItems.forEach((el, i) => {
    if (reduced) {
      reveal(el);
      return;
    }
    setTimeout(() => reveal(el), 120 + i * 90);
  });

  /* Scroll reveals */
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          reveal(entry.target);
          revealObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.1, rootMargin: "0px 0px -6% 0px" },
  );

  document.querySelectorAll(".reveal").forEach((el) => {
    if (!el.closest(".hero-inner")) revealObserver.observe(el);
  });

  /* Section scroll hook — marks sections in view for subtle CSS hooks */
  const sectionObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        entry.target.classList.toggle("is-in-view", entry.isIntersecting);
      });
    },
    { threshold: 0.15, rootMargin: "0px 0px -10% 0px" },
  );

  document.querySelectorAll("[data-scroll-section]").forEach((section) => {
    sectionObserver.observe(section);
  });

  /* Stat counters */
  if (!reduced) {
    function animateCount(el, end, suffix) {
      const start = performance.now();
      const duration = 1200;
      const tick = (now) => {
        const p = Math.min((now - start) / duration, 1);
        const eased = 1 - (1 - p) ** 3;
        const val = end * eased;
        el.textContent = (Number.isInteger(end) ? Math.round(val) : val.toFixed(1)) + suffix;
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }

    const statObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const el = entry.target;
          const raw = el.getAttribute("data-count") || el.textContent || "";
          const match = raw.match(/^([\d.]+)(.*)$/);
          if (match) animateCount(el, parseFloat(match[1]), match[2]);
          statObserver.unobserve(el);
        });
      },
      { threshold: 0.5 },
    );
    document.querySelectorAll("[data-count]").forEach((el) => statObserver.observe(el));
  }

  /* Feature card tilt (desktop hover only) */
  if (!reduced && window.matchMedia("(hover: hover)").matches) {
    document.querySelectorAll("[data-tilt]").forEach((card) => {
      const glow = card.querySelector(".feature-card-glow");
      card.addEventListener("mousemove", (e) => {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width;
        const y = (e.clientY - rect.top) / rect.height;
        card.classList.add("is-tilting");
        card.style.transform = `perspective(900px) rotateX(${(y - 0.5) * -5}deg) rotateY(${(x - 0.5) * 5}deg)`;
        if (glow) {
          glow.style.setProperty("--glow-x", `${x * 100}%`);
          glow.style.setProperty("--glow-y", `${y * 100}%`);
        }
      });
      card.addEventListener("mouseleave", () => {
        card.classList.remove("is-tilting");
        card.style.transform = "";
      });
    });
  }
})();
