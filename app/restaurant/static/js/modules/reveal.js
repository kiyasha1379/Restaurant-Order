/**
 * Entrance animation: elements marked with data-reveal fade in and rise
 * (24 px, 0.9 s, 100 ms stagger). Uses only transform and opacity, and does
 * nothing when the visitor prefers reduced motion or GSAP failed to load.
 */
const RISE_DISTANCE_PX = 24;
const DURATION_SECONDS = 0.9;
const STAGGER_SECONDS = 0.1;

function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function revealOnLoad() {
  const revealTargets = document.querySelectorAll("[data-reveal]");
  if (revealTargets.length === 0 || prefersReducedMotion() || !window.gsap) {
    return;
  }
  window.gsap.from(revealTargets, {
    y: RISE_DISTANCE_PX,
    opacity: 0,
    duration: DURATION_SECONDS,
    stagger: STAGGER_SECONDS,
    ease: "power2.out",
  });
}

/**
 * Scroll animation: elements marked with data-scroll-reveal rise in once, when they
 * first come into view. Same distance and duration as the entrance animation.
 */
export function revealOnScroll() {
  const targets = document.querySelectorAll("[data-scroll-reveal]");
  if (targets.length === 0 || prefersReducedMotion() || !window.gsap || !window.ScrollTrigger) {
    return;
  }
  window.gsap.registerPlugin(window.ScrollTrigger);
  window.ScrollTrigger.batch(targets, {
    start: "top 88%",
    once: true,
    onEnter: (batch) =>
      window.gsap.from(batch, {
        y: RISE_DISTANCE_PX,
        opacity: 0,
        duration: DURATION_SECONDS,
        stagger: STAGGER_SECONDS,
        ease: "power2.out",
        overwrite: true,
      }),
  });
}
