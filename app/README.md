# Restaurant website (Flask)

A bilingual (Persian right-to-left, English left-to-right) restaurant site: menu, online ordering, table reservation and an admin panel. It is a **demo** build; no real payment, SMS or e-mail is connected.

The plan is in `../docs/technical-plan.en.md`. What has been built so far is in `IMPLEMENTATION_LOG.md`.

## Requirements

- Python 3.11 or newer
- Git (optional)

## First run (Windows, PowerShell)

```powershell
cd D:\Project\Restaurant\app
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

copy .env.example .env          # then edit SECRET_KEY
$env:FLASK_APP = "wsgi.py"
flask db upgrade                # creates instance\restaurant.db with the two languages
flask run                       # http://127.0.0.1:5000
```

After the first `flask db upgrade`, load the interface texts and the sample data once:

```powershell
flask sync-ui-strings           # default texts in both languages
flask seed-demo                 # menu, builders, tables, staff, a customer, sample orders and bookings
```

Use `$env:APP_CONFIG = "demo"` (or put `APP_CONFIG=demo` in `.env`, as `.env.example` does) to show the "demo version" bar and to allow `flask reset-demo`. Configurations are `dev` (default), `demo`, `prod` and `test`.

If PowerShell blocks the activation script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

## Everyday commands

| Task | Command |
| --- | --- |
| Run the tests | `pytest` |
| Format the code | `black .` |
| Check style and docstrings | `ruff check .` |
| Create a migration after changing a model | `flask db migrate -m "what changed"` |
| Apply migrations | `flask db upgrade` |
| Add the sample menu, backgrounds and demo staff (safe to repeat) | `flask seed-demo` |
| Copy default interface texts into the database | `flask sync-ui-strings` |
| Create the first administrator (asks for e-mail, name, password) | `flask create-admin` |
| Delete ALL data and uploads and load the sample data again (demo mode only; asks first, `--yes` skips) | `flask reset-demo` |
| Save a consistent copy of the database into `instance/backups` and keep the newest 14 | `flask backup-db` |

## Admin panel

Open `http://127.0.0.1:5000/admin/login`. After `flask seed-demo` these accounts exist, all with the password `demo-pass-1234`: `admin@example.com`, `manager@example.com`, `cashier@example.com`, `kitchen@example.com`, `viewer@example.com`. **They are for the demo only; never keep them on a real server.** On a real installation run `flask create-admin` instead. The roles and what each may do are edited in the panel under "Users and roles".

Uploaded photos (dishes and builder options) are stored under `restaurant/static/uploads` (not in git). The "Custom builders" section edits the build-your-own pizza, sandwich and drink: steps, options, prices and pictures. "Tables and reservations" lists and confirms bookings, edits the floor plan, opening hours, closure days and booking rules.

The section "Settings" turns online ordering off for a while, sets the delivery fee, the payment methods and the contact details in the footer. "Site appearance" changes the brand name, accent colour and logo, the video and poster of every background, and the order of the home page sections and its main texts.

Schema changes go only through migrations, never by editing the database by hand.

## Demo walkthrough

After `flask seed-demo` (or `flask reset-demo`) the site is ready to show:

1. Home page (`/fa/`, `/en/`): scroll through the sections; flip a round card.
2. Menu: add dishes, open the cart, check out (pay on arrival, or "Pay online" for the test gateway page; its code and amount are fake). In the demo the customer sign-up code is always `12345`.
3. "Build your own": pizza, sandwich or drink with a live price.
4. Reservation: choose a day (Jalali calendar), a time and a table on the floor plan.
5. Admin (`/admin/login`, `admin@example.com` / `demo-pass-1234`): the kitchen board with live updates (move an order with the buttons), the dashboard, reservations, the menu, "Settings" (pause orders and watch the notice appear on the site) and "Site appearance" (accent colour, logo, backgrounds, section order).
6. `flask reset-demo --yes` returns everything to the start.

## Going live

The demo build is not for a real restaurant until these are done:

- `APP_CONFIG=prod` and a random `SECRET_KEY` (32+ characters) in the environment; the app refuses to start otherwise. In `prod` the test payment page, the demo bar and the demo accounts are off, cookies are HTTPS-only and security headers (including HSTS) are sent.
- Create the first administrator with `flask create-admin`; do not run `flask seed-demo` on a real server.
- Serve it from a Linux server with Gunicorn behind nginx: see `deploy/` (`gunicorn.conf.py`, `nginx.conf.example`, `restaurant.service.example`; `pip install -r requirements-prod.txt`). On Windows use Waitress instead (`pip install waitress`, `waitress-serve --port 8000 wsgi:app`).
- Online payment stays off (`PAYMENT_GATEWAY` empty) until a real gateway class is added in `restaurant/services/payment_gateway.py`. No SMS or e-mail is sent: sign-up codes are only written to the log until a real sender is added.
- Schedule `flask backup-db` (for example nightly) and copy `instance/backups` and `restaurant/static/uploads` somewhere else.
- The sample background videos carry a generator watermark; replace them from "Site appearance".

## Accessibility check

`tests/browser/a11y_check.js` runs axe-core on the main pages in both languages (see the comment at its top for the command). It reports no WCAG A or AA violations.

## Layout

See section 3 of the plan. In short: `restaurant/` is the application package (models, repositories, services, blueprints, templates, static), `tests/` holds the tests and `migrations/` the Alembic history.

## Fonts

Vazirmatn, Noto Naskh Arabic and Cormorant Garamond are served from `restaurant/static/fonts`. **B Nazanin** (Persian headings) is not a free font, so no file is shipped: it is used when installed on the visitor's computer, otherwise Noto Naskh Arabic is shown. To serve it from the site, put a licensed `BNazanin.woff2` in `restaurant/static/fonts` and add a `url()` source to the `B Nazanin` rule in `static/css/fonts.css`.

## Customer accounts

Customers register at `/fa/register` or `/en/register` and confirm their phone with a code. In the demo the code is always `12345`. After `flask seed-demo` a customer exists: `customer@example.com` or `09120000000`, password `demo-pass-1234`. The account pages are under `/<lang>/account`; messages sent from the contact page and the customer list are in the admin section "Customers and messages".

## Online payment (test gateway)

At checkout a customer can choose "Pay online". The `PAYMENT_GATEWAY` setting in `restaurant/config.py` is `mock`: the customer lands on a clearly marked test page with three buttons (successful, failed, cancel); no card is asked for and no money moves. An order enters the kitchen only after the payment is verified; after a failure the customer can retry or pay on arrival. Staff see every attempt, with a "Test" badge, on the order page. **Never run a real installation with `PAYMENT_GATEWAY=mock`**; a real bank is added as one more class in `restaurant/services/payment_gateway.py`.

