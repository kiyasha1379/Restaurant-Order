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

Use `$env:APP_CONFIG = "demo"` (or put `APP_CONFIG=demo` in `.env`) to show the "demo version" bar. Configurations are `dev` (default), `demo` and `test`.

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
| Reset the demo (arrives in a later phase) | `flask reset-demo` |

## Admin panel

Open `http://127.0.0.1:5000/admin/login`. After `flask seed-demo` these accounts exist, all with the password `demo-pass-1234`: `admin@example.com`, `manager@example.com`, `cashier@example.com`, `kitchen@example.com`, `viewer@example.com`. **They are for the demo only; never keep them on a real server.** On a real installation run `flask create-admin` instead. The roles and what each may do are edited in the panel under "Users and roles".

Uploaded photos (dishes and builder options) are stored under `restaurant/static/uploads` (not in git). The "Custom builders" section edits the build-your-own pizza, sandwich and drink: steps, options, prices and pictures. "Tables and reservations" lists and confirms bookings, edits the floor plan, opening hours, closure days and booking rules.

The section "Settings" turns online ordering off for a while, sets the delivery fee, the payment methods and the contact details in the footer. "Site appearance" changes the brand name, accent colour and logo, the video and poster of every background, and the order of the home page sections and its main texts.

Schema changes go only through migrations, never by editing the database by hand.

## Layout

See section 3 of the plan. In short: `restaurant/` is the application package (models, repositories, services, blueprints, templates, static), `tests/` holds the tests and `migrations/` the Alembic history.

## Fonts

Vazirmatn, Noto Naskh Arabic and Cormorant Garamond are served from `restaurant/static/fonts`. **B Nazanin** (Persian headings) is not a free font, so no file is shipped: it is used when installed on the visitor's computer, otherwise Noto Naskh Arabic is shown. To serve it from the site, put a licensed `BNazanin.woff2` in `restaurant/static/fonts` and add a `url()` source to the `B Nazanin` rule in `static/css/fonts.css`.

## Customer accounts

Customers register at `/fa/register` or `/en/register` and confirm their phone with a code. In the demo the code is always `12345`. After `flask seed-demo` a customer exists: `customer@example.com` or `09120000000`, password `demo-pass-1234`. The account pages are under `/<lang>/account`; messages sent from the contact page and the customer list are in the admin section "Customers and messages".

## Online payment (test gateway)

At checkout a customer can choose "Pay online". The `PAYMENT_GATEWAY` setting in `restaurant/config.py` is `mock`: the customer lands on a clearly marked test page with three buttons (successful, failed, cancel); no card is asked for and no money moves. An order enters the kitchen only after the payment is verified; after a failure the customer can retry or pay on arrival. Staff see every attempt, with a "Test" badge, on the order page. **Never run a real installation with `PAYMENT_GATEWAY=mock`**; a real bank is added as one more class in `restaurant/services/payment_gateway.py`.

