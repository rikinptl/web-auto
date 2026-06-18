const header = document.querySelector("[data-header]");
const navToggle = document.querySelector("[data-nav-toggle]");
const navMobile = document.querySelector("[data-nav-mobile]");
const progress = document.querySelector(".scroll-progress");

function onScroll() {
  const scrolled = window.scrollY > 24;
  header?.classList.toggle("is-scrolled", scrolled);
  if (progress) {
    const height = document.documentElement.scrollHeight - window.innerHeight;
    progress.style.width = height > 0 ? `${(window.scrollY / height) * 100}%` : "0%";
  }
}

navToggle?.addEventListener("click", () => {
  const isHidden = navMobile.hasAttribute("hidden");
  if (isHidden) navMobile.removeAttribute("hidden");
  else navMobile.setAttribute("hidden", "");
});

window.addEventListener("scroll", onScroll, { passive: true });
onScroll();

const revealItems = document.querySelectorAll(".reveal");
const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.12, rootMargin: "0px 0px -40px 0px" },
);
revealItems.forEach((item) => observer.observe(item));
