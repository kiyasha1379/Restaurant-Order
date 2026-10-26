/**
 * Loads and plays background videos only while they are on screen.
 *
 * Rules (technical plan, section 8):
 *  - a video file is not requested until its area is visible;
 *  - at most MAX_PLAYING videos play at once (the ones most in view);
 *  - phones, Save-Data and slow connections, and visitors who prefer reduced
 *    motion, only ever see the poster (data-mobile-mode="poster_only");
 *  - if a video fails, it is removed and the poster stays.
 */
const MAX_PLAYING = 2;
const PHONE_QUERY = "(max-width: 45rem)";
const VISIBLE_THRESHOLDS = [0, 0.25, 0.5, 0.75, 1];

function shouldStayOnPoster(area) {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return true;
  }
  const connection = navigator.connection;
  if (connection && (connection.saveData || /(^|-)2g$/.test(connection.effectiveType || ""))) {
    return true;
  }
  const onPhone = window.matchMedia(PHONE_QUERY).matches;
  return onPhone && area.dataset.mobileMode !== "video";
}

function prepare(video) {
  if (!video.src && video.dataset.src) {
    video.addEventListener("error", () => video.remove(), { once: true });
    video.addEventListener("playing", () => video.classList.add("is-playing"), { once: true });
    video.src = video.dataset.src;
  }
}

export function startLazyVideos() {
  const areas = Array.from(document.querySelectorAll("[data-lazy-video]"));
  const entries = areas
    .map((area) => ({ area, video: area.querySelector("video"), ratio: 0 }))
    .filter((entry) => entry.video && !shouldStayOnPoster(entry.area));
  if (entries.length === 0 || !("IntersectionObserver" in window)) {
    return;
  }

  const byArea = new Map(entries.map((entry) => [entry.area, entry]));

  function refresh() {
    const wanted = entries
      .filter((entry) => entry.ratio > 0 && entry.video.isConnected)
      .sort((a, b) => b.ratio - a.ratio)
      .slice(0, MAX_PLAYING);
    entries.forEach((entry) => {
      if (!entry.video.isConnected) {
        return;
      }
      if (wanted.includes(entry)) {
        prepare(entry.video);
        entry.video.play().catch(() => {});
      } else {
        entry.video.pause();
      }
    });
  }

  const observer = new IntersectionObserver(
    (changes) => {
      changes.forEach((change) => {
        const entry = byArea.get(change.target);
        if (entry) {
          entry.ratio = change.isIntersecting ? change.intersectionRatio : 0;
        }
      });
      refresh();
    },
    { threshold: VISIBLE_THRESHOLDS },
  );
  entries.forEach((entry) => observer.observe(entry.area));

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      entries.forEach((entry) => entry.video.pause());
    } else {
      refresh();
    }
  });
}
