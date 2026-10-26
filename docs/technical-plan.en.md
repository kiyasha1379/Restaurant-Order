# Restaurant Website: Technical Plan

*Written 2026-10-26. Online version with the two diagrams: https://claude.ai/artifact/CmvZy81hxn9oDUqQrropyJ*

## 1. Overview

This is a custom restaurant website, built first as a **demo**: customers browse the menu, build their own pizza, sandwich or drink, order for takeaway or delivery, and reserve a table; staff run everything from an admin panel. The site is bilingual (Persian right-to-left, English left-to-right) and uses rich animation that stays smooth on phones.

**In scope for the demo**

- Public site: home page with video sections, menu, custom builder, cart and checkout, live order tracking, table reservation on a floor plan, optional customer account.
- Admin panel with roles and per-section permissions.
- Payment: pay on site, plus a **mock** online gateway that behaves like a real one.
- Persian (Jalali) dates through one shared date picker.
- Backgrounds (videos and posters) driven by data, not hard-coded in templates.

**Out of scope for now:** a real payment gateway, real SMS or email, a third language, multiple branches, native apps, and real photography (placeholder images stand in).

**Goals**

1. A customer can complete an order end to end by the end of phase 4.
2. Two bookings can never overlap on the same table.
3. Every price is calculated on the server; the browser only previews.
4. Swapping the mock gateway for a real one later changes one setting and one class, nothing else.

## 2. Tech stack and architecture

The site is one Flask application that renders pages on the server with Jinja2 and also serves a few small JSON endpoints (live price quote, availability, order status). There is no separate front-end app. The only thing outside the application is the payment gateway, which is mocked for the demo.

| Layer | Choice | Why |
| --- | --- | --- |
| Backend | Python 3.12, Flask, blueprints, application factory | Small, readable, easy to test |
| Pages | Jinja2 server rendering, HTMX for small partial updates | Cart and order status update without a full reload |
| Database | SQLite (WAL mode, foreign keys on), SQLAlchemy 2, Alembic migrations | Enough for one restaurant; easy to move to PostgreSQL later |
| Auth | Flask-Login, roles and permissions in tables, argon2 or scrypt hashes | Per-section permissions edited from the admin panel |
| Security | Flask-WTF (CSRF), Flask-Limiter (rate limits), upload validation | Covers forms, login and file uploads |
| Front end | Plain JavaScript modules, CSS with design tokens, GSAP and ScrollTrigger | No framework needed; animations use only transform and opacity |
| Live updates | Server-sent events, with 5-second polling as a fallback | Order tracking and the kitchen queue |
| Dates | `jdatetime` on the server, one shared `JalaliCalendar` helper in the browser | Jalali calendar with no hand-written date math |
| Payments | `PaymentGateway` interface, `MockGateway` for the demo | Real gateway later without touching other code |
| Quality | pytest, ruff, black | Same checks on every phase |
| Fonts | Vazirmatn (text), B Nazanin (Persian headings, needs a licensed file), Noto Naskh Arabic fallback, Cormorant Garamond (English headings) | All served from our own server |

**Layer rules.** Each layer talks only to the one below it:

- **Blueprints** receive the request and return the response. No business logic.
- **Services** hold the rules: pricing, ordering, booking, payment. They can run and be tested without the web server.
- **Repositories** are the only code that writes queries.
- **Models** describe the shape of the data and nothing else.

A request enters through a blueprint, passes to a service, and reaches the database only through a repository. Payments go out through the gateway interface, which is the mock in the demo.

## 3. Project structure

Business rules live in `services`. Blueprints only take the request and return the response, so pricing, booking and payment can be tested without running the web app.

```text
Restaurant/                         # the project folder
├── docs/                          # plans, design and notes
│   ├── README.md
│   ├── technical-plan.en.md       # this plan
│   ├── technical-plan.fa.md       # the Persian plan
│   └── design/                    # design canvas boards (open in a browser)
└── app/                           # the Flask project
    ├── IMPLEMENTATION_LOG.md      # running report: what was built, phase by phase
    ├── README.md                  # how to install, run and test
    ├── wsgi.py                    # entry point for flask run
    ├── pyproject.toml             # black, ruff and pytest settings
    ├── requirements.txt           # runtime dependencies (+ requirements-dev.txt)
    ├── migrations/                # Alembic: every schema change goes here
    ├── tests/                     # unit tests for services, route tests for flows
    └── restaurant/                # the application package
        ├── __init__.py            # create_app()
        ├── config.py              # Dev, Demo and Test configuration classes
        ├── constants.py           # enums and named constants (languages, access levels)
        ├── extensions.py          # db, migrate (later: login, csrf, limiter)
        ├── database.py            # SQLite foreign keys and WAL mode
        ├── logging_setup.py       # console and rotating file logs
        ├── timeutils.py           # Tehran time helpers
        ├── text_catalog.py        # t(key) lookup (phase 2 moves it to the database)
        ├── template_context.py    # language, brand name, demo flag for every template
        ├── cli.py                 # flask seed-demo, flask reset-demo
        ├── models/                # one module per domain: language, setting, background, access, menu...
        ├── repositories/          # one class per aggregate; the only code that writes queries
        ├── services/              # business rules: language, settings; later pricing, orders, booking, payments/
        ├── blueprints/            # HTTP only: public, errors; later menu, cart, orders, booking, auth, admin, api
        ├── templates/             # base.html, macros/, partials/, errors/, one folder per area
        └── static/
            ├── css/               # fonts.css, tokens.css, base.css, components/, pages/
            ├── js/                # main.js, modules/, vendor/ (GSAP)
            ├── fonts/             # self-hosted .woff2 files
            └── uploads/           # menu photos, builder layers, backgrounds (not in Git)
```

## 4. Database

Tables are grouped by domain. Two principles hold everywhere: every translatable text lives in a separate `*_translations` table, and every price stored on an order is a snapshot, so changing the menu later never rewrites old orders. Money is stored as whole tomans; dates are stored as Gregorian ISO values in the `Asia/Tehran` time zone.

| Domain | Tables | Notes |
| --- | --- | --- |
| Language | `languages`, `ui_strings`, `ui_string_translations` | Exactly two rows, `fa` and `en`. English can be switched off; missing text falls back to Persian |
| Users and access | `users`, `roles`, `permissions`, `role_permissions`, `user_roles`, `addresses` | A customer account is optional. Roles and permissions are edited in the admin panel |
| Menu | `categories`, `dishes`, `dish_translations`, `category_translations`, `dish_images` | Each dish has a base price, an in-stock flag and a display order |
| Builder | `builders`, `builder_steps`, `builder_options`, plus translations | One generic model for pizza, sandwich and drink; a new type needs no code change |
| Orders | `orders`, `order_items`, `order_item_options`, `order_status_log` | `order_index` keeps sandwich layer order; prices are snapshots |
| Delivery and payment | `delivery_zones`, `payments` | Pay on site and online share one `payments` row shape; the mock gateway writes `MOCK-` transaction ids |
| Booking | `tables`, `reservations`, `opening_hours`, `special_closures` | Table position on the floor plan, capacity, status per reservation |
| Appearance | `backgrounds`, `site_sections` | Video, poster, dimming and mobile mode per background; order and visibility of home sections |
| Settings | `settings` | Key and value: delivery fee mode, payment toggles, reservation rules, contact details |

### Booking overlap rule

Two reservations on the same table collide when `start_a < end_b` and `start_b < end_a`. Only confirmed reservations block a table. The check and the insert run in one `BEGIN IMMEDIATE` transaction, so two simultaneous requests cannot both succeed. A pending reservation may overlap another, but confirming it is refused if a confirmed one already holds the slot, and the admin panel suggests another free table.

## 5. Routes and pages

All public routes carry a language prefix (`/fa/menu`, `/en/menu`) so each language has a stable, shareable address. Admin and API routes have no prefix.

| Area | Route | Purpose |
| --- | --- | --- |
| Home | `/<lang>/` | Full-screen sections with background videos and the framed pizza video |
| Menu | `/<lang>/menu`, `/<lang>/menu/<category>` | Dishes in round cards, cart drawer |
| Builder | `/<lang>/build/<type>` | Pizza, sandwich and drink builder with live price |
| Cart | `/<lang>/cart`, `POST /cart/add`, `POST /cart/update` | Cart kept in the session |
| Checkout | `/<lang>/checkout`, `/<lang>/order/<id>` | Takeaway or delivery, payment method, live tracking |
| Payment | `/pay/<order>/start`, `/pay/mock/<order>`, `/pay/callback/<gateway>` | Start payment, mock gateway page, return from the gateway |
| Reservation | `/<lang>/reserve`, `GET /api/availability` | Jalali date picker, time, guests, floor plan |
| Account | `/<lang>/account`, `/login`, `/register` | Orders, addresses and reservations |
| Admin | `/admin`, `/admin/orders`, `/admin/menu`, `/admin/builders`, `/admin/tables`, `/admin/customers`, `/admin/languages`, `/admin/users`, `/admin/site`, `/admin/settings` | One permission per section |
| API | `/api/quote`, `/api/orders/<id>/stream` | Live price quote and order status (server-sent events) |

The price is always computed on the server. The number the browser shows is only a preview: at checkout, `/api/quote` recomputes the same selection from the price tables.

## 6. Admin panel

The panel follows the "Admin" board of the design canvas and works on phones too (slide-in menu, cards instead of tables). Every section has its own permission. A role gets one of three levels per section: none, view or edit. At the view level every change button is hidden. A separate `money` permission decides who sees amounts and customer details inside orders, so the kitchen sees only the items.

| Section | Permission | What it manages |
| --- | --- | --- |
| Dashboard | `dash` | Today's orders and sales, busy hours, tonight's reservations, alerts (order waiting for approval, dish out of stock, missing translation) |
| Orders | `orders` | Live four-column board, list and history, detail and status log, accept or reject, receipt printing, sandwich layer order |
| Menu | `menu` | Dishes (photo, price, stock, chef's pick, Persian and English text), categories and their order |
| Builders | `builders` | Steps (single or multiple choice, required), options (price, layer image, stock, names), order, price preview |
| Tables and reservations | `tables` | Confirm or cancel with overlap protection and a suggested alternative table, floor-plan editor (move, capacity, close a table) |
| Customers and messages | `customers` | Registered and guest customers, addresses, contact-form messages |
| Languages | `languages` | Translation status for Persian and English, default language, switching English off, UI strings, untranslated list |
| Users and roles | `users` | Invite and block staff, roles, permission matrix |
| Site appearance | `site` | Background videos and posters, home section order and visibility, home texts, brand name, logo, accent color |
| Settings | `settings` | Opening hours and special closures, takeaway and delivery (fixed fee or zones), payment methods, reservation rules, contact details, pause online ordering |

Admin dates (special closures, the reservation day filter) use the same Jalali date picker as the public site.

## 7. Key technical decisions

- **SQLite in WAL mode:** concurrent reads and writes work, and `PRAGMA foreign_keys=ON` stays on everywhere. Enough for one restaurant; SQLAlchemy makes a later move to PostgreSQL simple.
- **Two fixed languages:** Persian (right-to-left) and English (left-to-right). Texts live in the database and are edited from the admin panel. Adding a third language is not a feature of the application.
- **Page direction:** only CSS logical properties (`margin-inline-start` and similar), and `dir` comes from the language record on `<html>`, so both languages use one stylesheet.
- **Server-side prices and snapshots:** the client never sends a price. The name and price of every chosen option are copied into `order_items` at the moment of ordering.
- **Cart in the session:** guests can order. After login the cart is merged into the account.
- **Pluggable payment:** a `PaymentGateway` interface with `start()` and `verify()`. Pay on site, the mock gateway and any future real gateway implement it. An order becomes "paid" only after `verify()` succeeds.
- **Live order status:** server-sent events for the customer and the kitchen queue, with a 5-second polling fallback if the proxy or host blocks streaming.
- **Animation limited to transform and opacity:** stays smooth on phones; every animation stops under `prefers-reduced-motion`.
- **Self-hosted assets:** fonts and JavaScript libraries are served from our server, not from a CDN, so the site works on networks where those CDNs are slow or blocked.
- **Security:** CSRF protection on every form, strong password hashing, login rate limits, and photo uploads accepted only after type and size checks.

## 8. Implementation rules

These rules come from the decisions made for the demo. Every phase must follow them.

### Demo mode

- A `DEMO_MODE` setting in `config.py`. When it is on, a small "demo version" bar appears on every page.
- No real external service is connected: no bank gateway, no SMS, no email. If phone login is needed, the verification code is fixed and printed on the page.
- `flask seed-demo` creates the sample data and `flask reset-demo` returns everything to the starting state.
- Sample photos and texts are labelled as samples. No real personal data goes into the demo.

### Mock payment gateway

- The `PaymentGateway` interface (`start()` and `verify()`) is kept. `MockGateway` sits next to "pay on site". The `PAYMENT_GATEWAY` setting picks the class through a factory, so a real gateway replaces it later without touching other code.
- "Pay online" sends the customer to `/pay/mock/<order>`. The page is clearly labelled "test gateway, no money is charged" and has three buttons: successful payment, failed payment, cancel. There is no card form.
- An order becomes "paid" only after `verify()` runs, even in mock mode, so the callback path is rehearsed exactly as with a real gateway.
- Mock transaction ids start with `MOCK-`, and the admin panel shows a "test" badge next to such payments.
- After a failed or cancelled payment the order stays "awaiting payment"; the customer can retry or choose pay on site.

### Jalali dates and the date picker

- All displayed dates are Jalali with Persian digits. The database stores Gregorian ISO values in `Asia/Tehran`; conversion happens only when showing or receiving a date. Iran has no daylight saving time, so the offset is constant.
- The server uses `jdatetime` (or `persiantools`); month lengths and leap years are never calculated by hand.
- One shared `DatePicker` component serves customer reservations, manual reservations in the admin panel, special closures and the reservation filter. Typing a date by hand is not allowed.
- The picker opens on the **current** Jalali year and month. The user can move to other months with the previous and next buttons, then picks a day.
- A month before the current one is closed. A month after the last bookable day (the "maximum advance booking" setting) is closed. Past days, closed days and days beyond the booking window are dimmed and not selectable.
- The week starts on Saturday, Friday has its own color, today has a ring.
- Validation runs in the browser and again on the server; the server decides.

### Backgrounds

- A `backgrounds` table holds every background: `key`, `video_path`, `poster_path`, `dim` (0 to 1), `enabled`, `mobile_mode` (poster only, or video). Keys cover each home section and the menu, reservation and builder pages. The admin "Site appearance" section edits them.
- One Jinja macro (`macros/bg.html`) and one stylesheet draw every background. A video address is never written inside a template (the design canvas inlines them only because it is a prototype).
- Layers: on the home page each section has its own `absolute` background; inner pages have one `fixed` background behind everything. A standard dark layer (dim value plus vignette) always sits on top of the video, and content sits above that layer, so text stays readable.
- Fallback chain: video, then poster, then a dark gradient. A missing file never leaves a blank page.
- Performance: only the video of the visible section plays (`IntersectionObserver`); the rest use `preload="none"` and stay paused, with at most two playing at once. On phones, with `prefers-reduced-motion`, `Save-Data` or a slow connection, only the poster is shown. The canvas removed visibility-based pausing because the prototype lives in a frame; the real site brings it back.
- Files: H.264 mp4 without audio, at most 720p and preferably under 3 MB, with a webp poster. Uploads are checked for type and size. Backgrounds are `aria-hidden` and have no controls.
- The framed pizza video on the home page is separate from backgrounds: a normal muted, looping video inside the frame.

### Fonts

- Vazirmatn for text and interface, B Nazanin for Persian headings, Cormorant Garamond for English headings. All are served from our server through `@font-face`.
- B Nazanin is not free. The site needs a licensed font file in `static/fonts`. Until then the stack falls back to Noto Naskh Arabic, which is free.

## 9. Coding standards

These standards apply to all code: Python, templates, CSS and JavaScript.

### No repeated code

- Every rule is written once. When two places look alike, the shared part moves into a function, class or template macro. Before writing something new, search for what already exists.
- Every repeated piece of interface (date picker, dish card, background, button) is one parameterized Jinja macro or partial, never a copy.
- A style needed in more than one place is written once in the shared CSS. Inline styles in templates are only for one-off values.
- Colors, spacing, radii, shadows and font sizes are CSS custom properties defined in `tokens.css`; raw numbers are not repeated elsewhere.
- Constants and texts live in one place (settings and translations), not scattered through the code.

### Naming of styles

- BEM naming: `.block`, `.block__element`, `.block--modifier`, for example `.dp`, `.dp__day`, `.dp__day--selected`.
- Names are English and kebab-case, and describe the role, not the look: `.btn--primary` is right, `.btn-yellow` is wrong.
- Shared classes have plain, stable names: `.btn`, `.card`, `.chip`, `.field`, `.stack`. Utility classes are few and start with `u-`, such as `u-visually-hidden`.
- A page-specific class starts with its page name, such as `.reserve-summary`.
- File order: `tokens.css`, then `base.css`, then `components/*.css` (one file per component), then `pages/*.css`.
- Selectors stay shallow (two levels at most). `!important` is used only with a comment explaining why.
- Layout uses logical CSS properties only, so right-to-left and left-to-right both work.

### Object-oriented Python and design patterns

- Every domain concept is a class, and the layers stay separate: models for data, repositories for queries, services for rules, blueprints for HTTP.
- Patterns and where they apply:
  - **Strategy:** payment gateways (`PaymentGateway` with `MockGateway` and later a real one) and delivery fee rules (fixed fee or by zone).
  - **Factory:** `create_gateway()` builds the gateway named by the `PAYMENT_GATEWAY` setting; `create_app()` builds the application.
  - **Repository:** each main table has an access class, for example `OrderRepository`, so services never write queries and tests stay simple.
  - **Service layer:** business rules live in `PricingService`, `OrderService` and `BookingService`.
  - **State:** order and reservation statuses and their allowed transitions live in one class, with an `Enum` for the status names.
  - **Observer (events):** events such as "order placed" feed the kitchen queue and live status.
  - **Decorator:** permission checks use `@permission_required`.
- A pattern is used only when it solves a real problem. A pattern without a reason, or an extra layer, is not allowed.
- Dependencies (repository, gateway) arrive through the constructor, not through global imports, so tests can replace them.
- All public functions and methods have type hints. SOLID principles guide class design: one responsibility per class, depend on abstractions.

### Clean code

- Names are English, complete and meaningful: `reservation_start_time`, not `rst`. Functions are verbs (`calculate_total`), classes are nouns (`ReservationService`), booleans start with `is_`, `has_` or `can_`.
- PEP 8 with `ruff` and `black`: `snake_case` for functions and variables, `PascalCase` for classes, `UPPER_CASE` for constants.
- A function does one thing and is short (about 20 lines), takes few parameters (three or four at most) and avoids deep nesting by returning early.
- No magic numbers or strings: use a named constant or an `Enum`.
- No dead code and no commented-out code. Errors are handled with specific exceptions, never a bare `except:`.
- Every business rule (pricing, booking overlap, payment confirmation) has unit tests.

### Comments

- All comments and docstrings are in English.
- Every module, class and public function has a docstring that says what it does and why, without repeating the code.
- Inline comments explain *why*: an unusual decision, a business rule, a limit. Obvious code gets no comment.
- CSS sections have a heading comment, and each template partial starts with a comment listing its parameters.

## 10. Design reference

The visual design lives in a design canvas with six boards. The code is built from these boards, which use cartoon placeholder images until real photos arrive.

| Board | What it shows |
| --- | --- |
| Main | Home page: hero with the framed pizza video, full-screen sections with video backgrounds, menu preview, order steps, reservation card, footer |
| Menu | Category chips, round dish cards, cart panel with takeaway or delivery and payment method |
| Builder | Pizza, sandwich and drink builder with sticky preview and live price |
| Reserve | Day chips and the Jalali date picker, time, guests, floor plan with free, busy and selected tables, summary |
| Admin | Full admin panel on desktop and phone |
| Style | Colors, type, components, motion rules |

**Colors**

| Role | Value |
| --- | --- |
| Page background | `#14100D` |
| Card surface | `#1E1814` |
| Raised surface | `#241C16` |
| Main text | `#F3E9DC` |
| Muted text | `#BCAA95` |
| Saffron accent (buttons, prices, emphasis) | `#E3A64B` |
| Ember (cancel, errors, Friday) | `#D9683A` |

**Type.** Vazirmatn for text, B Nazanin for Persian headings, Cormorant Garamond for English headings.

**Motion.** Elements fade in and rise 24 px over 0.9 s with a 100 ms stagger. Cards lift 8 px on hover. Adding to the cart flies a small dot to the cart icon. The selected table pulses. All motion stops under `prefers-reduced-motion`.

**Mobile.** At 720 px and below the header becomes compact with a bottom tab bar, tables turn into cards, and the floor plan scales with the container width.

**Direction.** Persian is right-to-left and English left-to-right. Numbers and Latin text inside Persian sentences are isolated with `<bdi dir="ltr">` so they never reverse.

## 11. Development process

Every phase produces a version that runs and can be demonstrated, and the next phase builds on it. Each phase follows the same loop:

1. **Plan:** read the phase's task list and the rules in sections 8 and 9; confirm any open question that blocks it.
2. **Data first:** write the models and the migration, then the repository and service classes with their unit tests.
3. **Pages:** build the blueprint and the Jinja templates from the matching design board, reusing macros and shared CSS.
4. **Behavior:** add the JavaScript module and animations; check reduced-motion and keyboard use.
5. **Test:** run unit tests, route tests for the main flow, and a manual check in Persian and English, on desktop and on a phone-sized window.
6. **Review:** check the phase against its "done when" line and the coding standards (no repeated code, names, comments).
7. **Demo:** reset the demo data, walk through the new flow, and note what changed in the plan.

**Definition of done for a phase**

- Every task in the phase is finished and the "done when" condition is true.
- Tests for the new business rules pass; `ruff` and `black` report nothing.
- Both languages and both text directions work, and there is no horizontal scrolling at 390 px width.
- No shared piece of interface or style is copied; new shared pieces are named by the rules.
- `flask seed-demo` and `flask reset-demo` still produce a working demo.

**Testing**

| Kind | What it covers |
| --- | --- |
| Unit tests | Pricing, booking overlap, order state changes, payment confirmation, Jalali conversion |
| Route tests | Cart to checkout to tracking, reservation, login and permissions, mock payment |
| Manual checks | Both languages, mobile layout, animations, reduced motion, slow connection with posters only |

**Working conventions**

- One Git branch per phase and small commits with clear messages; merge to `main` only when the phase is done.
- Three configurations: `Dev` (debug), `Demo` (`DEMO_MODE` on, seeded data) and `Test` (in-memory database).
- Schema changes go only through Alembic migrations, never by editing the database by hand.
- This plan is updated whenever a decision changes, so it always matches the code.

## 12. Build phases

The order is chosen so the site can take orders as early as possible (phase 4). Each phase lists its tasks and the condition that marks it as finished.

### Phase 0: Project setup

- Create the repository, virtual environment, `requirements.txt`, and the `ruff`, `black` and `pytest` configuration.
- Build `create_app()`, the `Dev`, `Demo` and `Test` configuration classes, and the `DEMO_MODE` switch.
- Create the folder skeleton from section 3 and a basic logging setup.
- Add `flask seed-demo` and `flask reset-demo` as empty commands to fill in later.

**Done when:** `flask run` starts, `pytest` runs (even with one smoke test), and linting passes.

### Phase 1: Foundation

- Write the core models and the first Alembic migration (users, languages, settings, backgrounds, menu tables).
- Create `base.html` with direction taken from the language record, `tokens.css`, `base.css` and the shared macros folder.
- Self-host the fonts (Vazirmatn, Noto Naskh Arabic or B Nazanin, Cormorant Garamond) and GSAP.
- Add error pages (404, 500) and the demo bar.

**Done when:** `flask db upgrade` builds an empty database and an empty home page renders in the design's colors and fonts.

### Phase 2: Two-language layer

- Create the `languages` table with `fa` and `en`, the `ui_strings` tables and the `t()` translation function with fallback to Persian.
- Add language-prefixed routes, the language switcher and automatic `dir` handling.
- Add number, price and Jalali date formatting helpers (`JalaliCalendar` in the browser, `jdatetime` on the server) with unit tests.

**Done when:** the same page opens at `/fa/` and `/en/`, flips direction correctly, and switching English off redirects to Persian.

### Phase 3: Menu and home page

- Models and repositories for categories, dishes, translations and images; seed a demo menu.
- Menu page with category chips and round dish cards; cart drawer shell.
- Home page sections with the framed pizza video, section video backgrounds from the `backgrounds` table, the `bg` macro and the visible-only video loader with poster fallback.
- Entrance and scroll animations, hover effects, mobile layout with the bottom tab bar.

**Done when:** home and menu match the Main and Menu boards in both languages, backgrounds fall back to posters on phones and with reduced motion, and no horizontal scrolling appears at 390 px.

### Phase 4: Cart and checkout (pay on site)

- `CartService` with the session cart, quantity changes and the add-to-cart animation.
- `PricingService` as the only place that computes prices; `/api/quote` for previews.
- Checkout for takeaway or delivery with address and delivery fee (fixed fee first), and pay on site.
- `orders`, `order_items`, `order_item_options` and the status log; `OrderService` with the order state class.
- Order confirmation and tracking page with server-sent events and the polling fallback.

**Done when:** a visitor can place a takeaway and a delivery order, see live status changes, and the stored prices equal the server calculation.

### Phase 5: Admin panel and roles

- Login with Flask-Login; seed roles and permissions; `@permission_required` and view-only mode.
- Admin shell (sidebar, mobile drawer), dashboard, live order board, order detail with status log and receipt printing.
- Menu management with photo upload and validation; languages section; users and roles with the permission matrix.

**Done when:** an admin can run the whole order flow from the panel, a cashier role sees amounts, the kitchen role does not, and a view-only role cannot change anything.

### Phase 6: Builder (pizza, sandwich, drink)

- Generic models for builders, steps and options with translations, and seed data for the three types.
- Builder page: step navigation, single and multiple choice, layered preview with a sticky panel, and the live price from `/api/quote`.
- Add built items to the cart, store `order_index` for layer order, and show layers in the order detail.
- Admin "Builders" section: steps, options, prices, layer images, stock, order, price preview.

**Done when:** a customer builds a sandwich, the price matches the server, and the kitchen sees the layers in the right order.

### Phase 7: Table reservation

- Models for tables, reservations, opening hours and special closures.
- The shared `DatePicker` (Jalali, current month by default, month navigation, dimmed unavailable days), time slots, guest count, and the floor plan with free, busy and selected tables.
- `BookingService` with the `BEGIN IMMEDIATE` overlap check, `GET /api/availability`, confirmation page, and the "maximum advance booking" rule.
- Admin "Tables and reservations": confirm or cancel, suggested alternative table, floor-plan editor, manual reservation, closures with the date picker.

**Done when:** two simultaneous requests for the same table and time cannot both succeed, and only free days appear selectable.

### Phase 8: Customer account

- Registration and login (phone or email with password; in demo mode the verification code is fixed).
- Address book, order history, reservation list, and merging the guest cart after login.
- Admin "Customers and messages" section with the contact form messages.

**Done when:** a registered customer reorders from history and sees their reservations, and a guest cart survives login.

### Phase 9: Mock online payment

- `PaymentGateway` interface, `MockGateway`, `create_gateway()` factory and the `PAYMENT_GATEWAY` setting.
- `/pay/<order>/start`, the test gateway page with success, failure and cancel, and the callback that calls `verify()`.
- The `payments` table with `MOCK-` ids, a "test" badge in the admin panel, and retry or switch to pay on site after failure.

**Done when:** all three outcomes behave correctly, an order is "paid" only after `verify()`, and no card data is ever collected.

### Phase 10: Site appearance and settings

- Admin "Site appearance": upload and replace background videos and posters, dimming, mobile mode, home section order and visibility, home texts, brand name, logo, accent color.
- Admin "Settings": opening hours, delivery fee (fixed or zones), payment methods, reservation rules, contact details, pause online ordering.

**Done when:** changing a background or a setting in the panel changes the public site with no code edit.

### Phase 11: Polish and demo readiness

- Complete the tests for pricing, booking and payment; fix gaps found in earlier phases.
- Optimize photos and videos (size limits from section 8); test on a real phone and on a slow connection.
- Accessibility pass: focus order, labels, contrast, reduced motion.
- Production settings: Gunicorn behind a reverse proxy, secure cookies, database backup script.
- Final seed data, the `reset-demo` walkthrough, and a short README that explains how to run and demo the site.

**Done when:** a fresh install runs the full demo from a reset, every item in the definition of done holds, and this plan matches the code.

## 13. Risks, open questions and later items

**Risks**

| Risk | Effect | Plan |
| --- | --- | --- |
| CDNs and Google Fonts are slow or blocked on some networks in Iran | Missing fonts and animation | Self-host fonts and libraries from phase 1 |
| B Nazanin is not a free font | License problem on the public site | Use a licensed file, or keep the free Noto Naskh Arabic fallback |
| Several background videos on phones | Slow load, data use | Poster-only mode on phones, one visible video at a time, size limits |
| Real photos and transparent builder layers are not ready | Cartoon placeholders stay visible | Placeholders are data, so swapping images needs no code change |
| Server-sent events blocked by a proxy or host | Live status stops updating | 5-second polling fallback is built in |
| Design canvas is not code | Differences appear during conversion | Build from the boards, then compare each page against its board in every phase |
| Shared files (`datepicker.js`, `datepicker.css`) may not load in the canvas viewer | Date picker unstyled in the prototype only | Inline them in the boards if needed; the real site is unaffected |

**Open questions**

1. **Delivery fee:** a fixed amount, or per zone (`delivery_zones`)? The admin settings support both; the default for the first build is a fixed fee.
2. **Guest checkout:** may a visitor order with only a name and phone number, or must they log in? The plan assumes guests can order.
3. **Currency display:** one currency for both languages (toman), or each language with its own? The plan assumes toman everywhere.
4. **Hosting:** inside Iran or abroad? It affects self-hosting of assets and, later, the choice of a real payment gateway.
5. **B Nazanin file:** will a licensed font file be provided, or do we keep the free fallback?

**Later items (not in the demo)**

- A real payment gateway (a new class behind the existing interface).
- Real photos and builder layers with background removal.
- Restoring scroll-controlled video on desktop only.
- Real SMS or email notifications.
- Removing watermarks from the generated background videos.
