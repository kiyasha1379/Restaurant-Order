# Implementation log

A running report of what was built, in order. Each phase has its tasks, the decisions made, how it was checked, and anything that differs from the plan. Newest phase last. The plan is `../docs/technical-plan.en.md`; the rules are its sections 8 and 9.

## Status

| Phase | Name | Status |
| --- | --- | --- |
| 0 | Project setup | Done (2026-10-26) |
| 1 | Foundation | Done (2026-10-26) |
| 2 | Two-language layer | Done (2026-10-26) |
| 3 | Menu and home page | Done (2026-10-26) |
| 4 | Cart and checkout (pay on site) | Done (2026-10-26) |
| 5 | Admin panel and roles | Done (2026-10-26) |
| 6 | Builder | Next |
| 7 | Table reservation | Not started |
| 8 | Customer account | Not started |
| 9 | Mock online payment | Not started |
| 10 | Site appearance and settings | Not started |
| 11 | Polish and demo readiness | Not started |

## Phase 0: Project setup (2026-10-26)

**Done**

- Project folder split into `docs/` (plans, design) and `app/` (the Flask project).
- `requirements.txt` (runtime) and `requirements-dev.txt` (adds pytest, ruff, black); `pyproject.toml` with the black, ruff and pytest settings; `.gitignore`; `.env.example`.
- `create_app()` application factory with `overrides` for tests; `wsgi.py` entry point.
- Three configurations in `config.py`: `DevConfig`, `DemoConfig` (`DEMO_MODE` on) and `TestConfig` (in-memory database). Chosen by name or by the `APP_CONFIG` variable.
- Folder skeleton for models, repositories, services, blueprints, templates and static files, matching section 3 of the plan.
- Logging: console always, rotating file `instance/logs/app.log` outside tests.
- `flask seed-demo` and `flask reset-demo` exist as empty commands.

**Checked**: `flask run` starts, `pytest` runs, `ruff` and `black` report nothing.

## Phase 1: Foundation (2026-10-26)

**Done**

- **Models** (SQLAlchemy 2, typed): `Language`, `Setting`, `Background`, `User`, `Role`, `Permission`, `RolePermission` (+ `user_roles`), `Category`, `CategoryTranslation`, `Dish`, `DishTranslation`, `DishImage`. Shared pieces are written once: `TimestampMixin`, `TranslationMixin` (language key of every `*_translations` table) and the `enum_type()` column helper.
- **Rules inside the schema**: only `fa` and `en` are allowed as language codes; background `dim` must be 0 to 1; a dish price cannot be negative; one translation per language per row; foreign keys are enforced.
- **First Alembic migration** builds all tables and inserts the two language rows (Persian default, English) because the site cannot work without them.
- **SQLite**: foreign keys on and WAL mode for every connection (`database.py`).
- **Layers**: `BaseRepository` plus `LanguageRepository`, `SettingRepository`, `BackgroundRepository`; `LanguageService` (Persian fallback) and `SiteSettingsService` (brand name). Dependencies come in through constructors.
- **Templates**: `base.html` (`lang` and `dir` come from the language record), `macros/ui.html` (`button_link`), `partials/demo_bar.html`, home page, and 404 / 500 pages that still render when the database is unavailable.
- **Styles**: `tokens.css` (all colours, spacing, radii, shadows, fonts, motion values), `base.css`, `components/button.css`, `components/demo-bar.css`, `pages/home.css`, `pages/error.css`. BEM names and logical properties only.
- **Fonts, self-hosted as .woff2**: Vazirmatn (6 weights), Noto Naskh Arabic (3), Cormorant Garamond (3). B Nazanin is declared with `local()` only (not free; no file shipped).
- **GSAP 3.12.5 and ScrollTrigger** vendored in `static/js/vendor`; `main.js` and `modules/reveal.js` give the entrance animation (rise 24 px, 0.9 s, 100 ms stagger, transform and opacity only, off under reduced motion).
- **Demo bar** shown when `DEMO_MODE` is on.

**Checked**

- 34 automated tests pass: configurations, constraints, repositories, services (with fake repositories), pages in both directions, demo bar, 404 and 500, a page with no database, and the migration (it builds every table and equals the models).
- `ruff` and `black` report nothing.
- In a real browser at 1280 px and 390 px: the page renders in the design colours and fonts, right-to-left in Persian, no horizontal scrolling, no failed requests, GSAP loaded.
- English (left-to-right) is covered by a test; it has not been looked at in a browser yet (the language switch arrives in phase 2).

**Differences from the plan, and why**

- **Python 3.11+** instead of 3.12: the code uses `StrEnum` (3.11). 3.12 also works.
- **Package name**: the application package is `restaurant/` inside `app/` (the plan sketch used `app/app/`). Section 3 of the plan was updated to match.
- **Texts through `t(key)` from a small in-code catalog** (`text_catalog.py`). The `ui_strings` tables belong to phase 2; templates already call `t()`, so phase 2 only swaps the lookup.
- **Tables left for their phases**: `ui_strings` and its translations (phase 2), `addresses` (phase 8), `site_sections` (phase 10).
- **Password hashing** will use Werkzeug's scrypt in phase 5 (the plan allowed argon2 or scrypt).
- **`tzdata`** is a dependency because Windows has no time zone database for `Asia/Tehran`.
- **Gunicorn does not run on Windows.** Phase 11 will pick the production server for the real host (Gunicorn on Linux, or Waitress).

## Phase 2: Two-language layer (2026-10-26)

**Done**

- **Texts in the database**: `ui_strings` and `ui_string_translations` (second migration). `Translator` (the `t("key")` in templates) looks a key up in this order: stored text in the language, default text in the language, stored Persian, default Persian, the key itself. Empty stored text counts as missing. Defaults live in `default_texts.py` (replaces the phase 1 `text_catalog.py`); `flask sync-ui-strings` copies missing defaults into the database and never overwrites an edit.
- **Language routes**: every public route is under `/<lang_code>` (`/fa/...`, `/en/...`). The prefix is checked in one place (`blueprints/language_routing.py`): unknown code gives 404, a switched-off language redirects to the default one, and `url_for` fills `lang_code` in by itself. `/` redirects to the default language.
- **Language service rules**: Persian can never be switched off and is the built-in fallback; English can be switched off. A broken or unmigrated database still renders Persian.
- **Switcher** in the header (`partials/language_switcher.html`): links to the same page (and query) in the other language; hidden when only one language is on; on error pages it links to the other language's home page.
- **Formatting** (`formatting.py`, plus Jinja filters `number`, `price`, `jdate`, `jdate_numeric`, `jtime`, `jdatetime`): numbers with separators, prices in tomans, Jalali dates; Persian digits only in Persian. The date is Jalali in both languages (plan, section 8); in English it is written with Latin digits and transliterated month names ("4 Aban 1405").
- **Browser calendar** `static/js/modules/jalali-calendar.js` (ES module, both languages): conversion, leap years, month lengths, week starting on Saturday, add days/months, parsing and formatting. The design canvas date picker (month grid) is built on top of it in phase 7.
- Per-request values (language, translator) are cached on the request itself rather than on `flask.g`, so they cannot leak between requests.

**Checked**

- 60 tests pass. New ones: formatting (digits, numbers, prices, five known Jalali dates, long dates in both languages), translator fallback order, sync idempotence and no overwrite, route behaviour (redirects, 404, English off, switcher, direction), and the browser calendar.
- The browser calendar and `jdatetime` agree for every one of the 25,933 days from 1990 to 2060 (a test runs Node.js and compares). Node.js tests also cover leap years, Friday, formatting and parsing. Both tests skip themselves when Node.js is not installed.
- In a real browser at 390 px and 1280 px: `/fa/` is right-to-left with the heading font stack for Persian, `/en/` is left-to-right with Cormorant Garamond, the switcher links to the other language, the English 404 page is English, no horizontal scrolling and no failed requests.

**Differences from the plan**

- The plan lists "number, price and Jalali date formatting helpers ... with unit tests" in phase 2; the date picker grid itself stays in phase 7 as planned.

## Phase 3: Menu and home page (2026-10-26)

**Done**

- **Menu data**: `dish_translations` gained `ingredients` and `serving_note` (third migration; existing rows get an empty text). `CategoryRepository` and `DishRepository` read visible items in menu order; `MenuService` turns them into `CategoryView` / `DishView` in the visitor's language, falling back to Persian, then to any text. `TranslationMixin` now loads the language row with the text so the code is at hand.
- **Demo content**: `flask seed-demo` adds 8 backgrounds, 5 categories (kebab, stew, pizza, starter, drink) and 11 dishes with Persian and English texts. It only adds what is missing, so running it twice changes nothing. Data lives in `seed/demo_data.py`, logic in `seed/seed_service.py`.
- **Backgrounds** (plan, section 8): the `backgrounds` table drives `macros/background.html` (`backdrop` and `framed_video`). Fallback chain: video, then poster, then the dark gradient in CSS. `modules/lazy-video.js` requests a video file only when its area is on screen, plays at most two at once, pauses off-screen ones and when the tab is hidden, and shows only the poster on phones (unless the row says `video`), with Save-Data, a 2G connection or reduced motion. A video that fails to load is removed and the poster stays.
- **Home page**: full-screen sections from the design: hero with the framed pizza video and floating chips, four ways to order (flip cards), chef's picks (round dish cards), three steps, reservation teaser, contact footer, side dots that follow the section on screen, entrance and scroll-in animation (GSAP; nothing is hidden when GSAP or JavaScript is missing).
- **Menu page**: category chips (links that work without JavaScript, and switch instantly with it), the round dish cards, and the cart panel shell (empty state, real cart in phase 4).
- **Round dish card** (`macros/dish.html`, `dish-card.css`, `dish-card.js`): tap flips to description, ingredients and serving note; name tag, price pill and add button; sold-out dishes show a label instead of the button. The add button fires a `cart:add` event with the dish id; phase 4 listens to it.
- **Chrome**: sticky header with brand, links, language switcher, cart pill; phone bottom tab bar; footer. Links are listed in `navigation.py` and appear only when their page exists, so builder, reservation and account show up by themselves in their phases. The home page hides the "ways to order" cards and the reservation section the same way.

**Checked**

- 90 tests pass (30 new: menu repositories and service with fallback, hidden items, order, chef's picks, seed idempotence and bilingual content, every seeded media file exists, menu and home pages in both languages, category query, nav and tab bar, background macro with video, poster only, disabled and missing rows, home with no menu data).
- `ruff`, `black` and the Node.js calendar tests are clean.
- Real browser (`tests/browser/*.js`): no horizontal scroll at 1440 and 390 px in both languages; no failed requests or console errors; on desktop the hero video and the framed video play and the other videos stay unrequested; on a phone no video is requested at all; flipping a card, the `cart:add` event and the category switch work.

**Bugs found and fixed while testing**

- The category filter joined `categories` twice (SQL "ambiguous column"); fixed and covered by a test.
- A Jinja filter on a constant (`{{ 0|number }}`) is evaluated once when the template is compiled, which froze one language's digits for every later request. Values now come from the context (`cart_total`), and a test renders fa, en, fa to guard it.
- The home page crashed when the database was not migrated yet; it now logs the error and shows the page without the chef's picks.

**Differences from the plan, and why**

- **Scroll behaviour**: the design draft hijacks the mouse wheel to jump between screens. The app uses CSS `scroll-snap-type: y proximity` instead, so the visitor is never trapped and keyboard, touch and screen readers keep their normal scrolling.
- **Pizza video** plays on loop while visible. The draft's label said it advances with scrolling, but its own script only plays it.
- **Sample media** (`static/media/backgrounds/`) are the design draft's stand-ins; they carry a video-maker watermark in the corner and must be replaced from the admin panel in phase 10.
- **Dishes have no photos yet**: they show the labelled placeholder gradient from the design ("Food photo"). Uploads arrive with the admin menu screen in phase 5.
- **Contact details** (address, hours, phone) are texts for now and move to settings in phase 10.
- B Nazanin is still not bundled (fallback Noto Naskh Arabic), as before.

## Phase 4: Cart and checkout, pay on site (2026-10-26)

**Done**

- **Orders in the database** (fourth migration): `orders`, `order_items`, `order_item_options` (used by the builder in phase 6) and `order_status_log`. Names and prices on an order are snapshots (both languages), so editing or deleting a dish never changes an old order.
- **Cart** (`CartService`, `cart_session.py`): lives in the visitor's session; it keeps only dish id and quantity, never a price. Quantities are capped at 20, damaged session data is ignored. The storage is injected, so tests use a plain list.
- **Pricing** (`PricingService`): the only place that computes money. Hidden, sold-out or deleted dishes are reported and dropped, never charged. Delivery fee is a `DeliveryFeeStrategy` (Strategy pattern); `FixedDeliveryFee` reads `delivery_fee` from the settings (default 30,000 tomans; broken values fall back to the default). Delivery zones will add a second strategy in phase 10.
- **Order state class** (`OrderStatusMachine`): placed, preparing, ready, out for delivery (delivery only), completed, cancelled. Takeaway is completed from "ready"; cancelling is allowed until the order is final.
- **OrderService**: prices the cart again on the server, stores the order with its lines and a first log entry, moves status with rule checks and a log entry each time. The tracking address uses an unguessable token, not the numeric id.
- **JSON API** (`/api/...`, `blueprints/api.py`): `GET /api/cart`, `POST /api/cart/add`, `POST /api/cart/update`, `GET /api/quote?fulfillment=`, `GET /api/orders/<token>/status` and `/stream` (server-sent events). The language comes from `?lang=`. Every write needs the CSRF token (Flask-WTF `CSRFProtect` is on for the whole site from now on; the page gives the token in a `<meta>` tag).
- **Pages**: cart page, checkout (name, Iranian mobile number with Persian digits accepted, takeaway or delivery with address, pay on arrival, notes; errors in the page language), and the order page with a live timeline. The menu cart panel, header badge, phone cart bar, toasts and the "dot flies to the cart" animation (GSAP; skipped for reduced motion) are in `cart.js`.
- **Live status**: the stream polls the database (so it works with several server processes), sends only changes plus keep-alives, and ends at a final status or after 10 minutes. If streaming fails or `EventSource` is missing, the page polls every 5 seconds.
- **Demo helpers**: in the demo configuration the order page has a "next status" button; `flask advance-order <id>` does the same from the command line. The admin kitchen board replaces both in phase 5.

**Checked**

- About 200 automated tests pass: cart rules, phone cleaning, pricing (fees, unavailable dishes, snapshots), the state class, order service (stored prices equal the server calculation, snapshot survives menu changes and dish deletion), the stream (without waiting), the JSON API (including rejected input, language, CSRF on), checkout pages in both languages, and the migration equals the models.
- Real browser, desktop and 390 px phone: add dishes (animation, badge, toast, cart bar), change quantities, delivery quote updates fee and total, order is placed, live status changes without reloading through the stream, and through polling when `EventSource` is removed; no failed requests, console errors or horizontal scroll.

**Bugs found and fixed while testing**

- A checkout whose cart had just lost a sold-out dish silently ordered the rest. It now returns to the checkout page with a notice so the customer sees the changed cart first.
- `RadioField` choices as tuples are deprecated; the form uses `SelectChoice`, and `requirements.txt` now needs WTForms 3.2 or newer.

**Differences from the plan, and why**

- **Tracking address** is `/<lang>/order/<token>` (plan said `<id>`): a numeric id would let anyone read other people's orders.
- **JSON routes** are all under `/api/` (`/api/cart/add`, `/api/cart/update`) instead of `/cart/add`: one prefix, one blueprint.
- **Observer pattern**: not added yet. Nothing consumes in-process events today (the stream reads the database), and a pattern without a consumer is against the coding rules. It comes in phase 5 only if the kitchen board needs it.
- **Delivery and payment choices** on the cart panel of the design draft moved to the checkout page, where the address and fee belong. Online payment appears there in phase 9.

## Phase 5: Admin panel and roles (2026-10-26)

**Done**

- **Staff sign-in** (`/admin/login`): Flask-Login sessions, scrypt password hashes (8 characters minimum), a rate limit on the sign-in form (Flask-Limiter), a blocked account is signed out at once, and the "next" address is only followed when it stays inside `/admin`. `flask create-admin` makes the first account; `flask seed-demo` also adds one demo account per default role (password `demo-pass-1234`, **demo only**).
- **Permissions**: eleven permissions (dash, orders, menu, builders, tables, customers, languages, users, site, settings, money). A role gives each one a level (none, view, edit); a user holds several roles and gets the highest level on each. `money` is a yes/no switch: without it, amounts and customer details are hidden (the kitchen role). The system role "administrator" always has full access and cannot be changed or deleted. Every admin route is guarded by `@permission_required(key, level)`; routes that change data need EDIT. No access shows a 403 page inside the panel; signed-out visitors go to the sign-in page.
- **Lockout protection** (`StaffService`): a change that would leave nobody able to edit users and roles is refused; you cannot block your own account; a role that still has users cannot be deleted.
- **Panel shell**: sidebar with only the sections the user may open, drawer on phones, panel language switch (Persian or English, kept in the session; the panel has no language prefix), waiting-orders badge.
- **Dashboard**: today's orders and sales (sales only with `money`), in-progress count, busy hours, alerts (untranslated dishes, sold-out dishes).
- **Orders**: live kitchen board (new, preparing, ready, done today) updated by server-sent events with a 5-second polling fallback, status change and cancel with log, history with search and paging, order page, printable receipt. Kitchen sees only items and note.
- **Menu**: dishes and categories (create, edit, delete, order up/down, stock/visible/chef's pick switches, filter by category, "missing English" filter). Photo upload (`ImageStorage`): the bytes are checked with Pillow (JPEG, PNG or WebP, at most 5 MB, at least 200 px), then re-encoded to WebP (at most 1200 px, EXIF turned and removed) under a random name, so the original file name and metadata never reach the site.
- **Languages**: translation progress per language (dishes, categories, interface texts), English on/off (off sends `/en` to Persian), default language, and an editor for every interface text (search, "only missing", paging; an empty field returns to the built-in text; only changed texts are stored).
- **Users and roles**: staff list and form (create, edit, password change, block), role list, and the permission matrix (radio buttons; on phones each section becomes a row of three labelled choices).
- **Texts**: all admin texts are in `admin_texts.py` in both languages. A test fails if a template or admin code uses a text key that does not exist.

**Checked**

- About 340 automated tests pass (about 160 new): permission levels and roles, sign-in and rate limit, CSRF, lockout rules, kitchen privacy, order board and search, photo validation and cleanup, menu forms, languages and text editor, users and roles, and the text-key check.
- Real browser, desktop 1366 px and phone 390 px: every new page loads with no horizontal scroll, no console errors and no failed requests; a photo uploaded in the dish form shows on the page after saving; a new order appeared on an open kitchen board in about 1.3 seconds without reloading.

**Bugs found and fixed while testing**

- The test client kept the previous request's user (Flask `g` lives as long as the app context in tests); the fixture now forgets it between requests.
- Without a `user_loader`, Flask-Login signed everybody out on every request; added.
- Role matrix on a phone overflowed by 50 px; the table turns into per-section rows under 48 rem.
- Dev server left over from an earlier session served old routes (404 everywhere); always restart it after pulling new code.

**Differences from the plan, and why**

- **Panel language** is stored in the session, not in the address: the plan's `/admin` has no language prefix.
- **Observer pattern** is still not added: the board reads a change marker (order count plus the newest status-log id) from the database, which also works with several server processes.
- Sections of later phases (builders, tables, customers, site, settings) are in the permission matrix already, but get a sidebar entry only when their pages exist.
