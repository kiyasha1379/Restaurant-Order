/**
 * Keeps --header-height equal to the real sticky header, and highlights the
 * side dot of the section that is on screen (home page).
 */
function syncHeaderHeight() {
  const header = document.querySelector("[data-site-header]");
  if (!header) {
    return;
  }
  const apply = () => {
    document.documentElement.style.setProperty("--header-height", `${header.offsetHeight}px`);
  };
  apply();
  window.addEventListener("resize", apply);
}

function highlightActiveDot() {
  const sections = Array.from(document.querySelectorAll("[data-section]"));
  const dots = new Map(
    Array.from(document.querySelectorAll("[data-section-link]")).map((dot) => [
      dot.dataset.sectionLink,
      dot,
    ]),
  );
  if (sections.length === 0 || dots.size === 0 || !("IntersectionObserver" in window)) {
    return;
  }
  const observer = new IntersectionObserver(
    (changes) => {
      changes.forEach((change) => {
        if (change.isIntersecting) {
          dots.forEach((dot, id) => {
            const active = id === change.target.id;
            dot.classList.toggle("is-active", active);
            if (active) {
              dot.setAttribute("aria-current", "true");
            } else {
              dot.removeAttribute("aria-current");
            }
          });
        }
      });
    },
    { rootMargin: "-45% 0px -45% 0px" },
  );
  sections.forEach((section) => observer.observe(section));
}

export function startSectionNav() {
  syncHeaderHeight();
  highlightActiveDot();
}
