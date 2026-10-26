/**
 * Site-wide script. Loaded as a module after GSAP on every page.
 * Page-specific behaviour lives in its own module and is started here.
 */
import { startBuilder } from "./modules/builder.js";
import { startCart } from "./modules/cart.js";
import { startCategoryFilter } from "./modules/category-filter.js";
import { startCheckout } from "./modules/checkout.js";
import { startConfirmForms } from "./modules/confirm-forms.js";
import { startDateFields } from "./modules/date-picker.js";
import { startDishCards } from "./modules/dish-card.js";
import { startLazyVideos } from "./modules/lazy-video.js";
import { startOrderTracker } from "./modules/order-tracker.js";
import { startReserve } from "./modules/reserve.js";
import { revealOnLoad, revealOnScroll } from "./modules/reveal.js";
import { startSectionNav } from "./modules/section-nav.js";

startSectionNav();
startLazyVideos();
startDishCards();
startCategoryFilter();
startCart();
startBuilder();
startCheckout();
startConfirmForms();
startDateFields();
startReserve();
startOrderTracker();
revealOnLoad();
revealOnScroll();
