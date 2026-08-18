# Implementation Plan — Banking Transaction Categorization

Source requirements: `docs/Senior_Engineer_Assessment_SOUS (2).pdf`.
Sample data: `docs/transaction_history (3).xls` (despite the extension, this is a
raw CSV export — 1000 rows, columns `Transaction ID, Amount, Timestamp,
Description, Transaction Type, Account Number`; 20 distinct `Description`
templates repeat across rows, dates span 2023-08 to 2024-08, `Transaction
Type` is `debit`/`credit` and uncorrelated with the sign of `Amount`).

This file is updated after each step with what was actually decided/verified,
so it doubles as a running decision log.

## Confirmed decisions

- **Project location**: Django project lives at the repo root (this
  directory), replacing the empty PyCharm scaffold (`main.py`,
  `pyproject.toml`).
- **Stack**: Django + Django REST Framework, PostgreSQL, Docker Compose, as
  instructed. Base layout borrowed from `~/Job/Projects/project_example`
  but trimmed hard — that example includes Celery, Redis, JWT auth,
  dj-rest-auth, CORS, a `users` app. None of that is needed for a
  read/write transactions API with no auth requirement, so it is dropped
  per "avoid overengineering". Kept: `drf-spectacular` for OpenAPI/Swagger
  docs (directly satisfies the "API documentation" requirement for free),
  `python-decouple` for env config, `gunicorn` for serving, `psycopg2`.
- **AI provider**: OpenAI API (`openai` Python SDK), selected via
  `OPENAI_API_KEY`/`OPENAI_MODEL` (default `gpt-4o-mini`). Originally
  Anthropic (matching the tool used to build the project), but switched
  because enabling billing on Anthropic required identity/government
  verification the user couldn't complete, whereas an OpenAI key was
  already available. Categorisation service is written behind a small
  interface (`categorize_batch`/`source`) so the provider is swappable —
  this was in fact exercised for real, not just theoretical. When
  `OPENAI_API_KEY` is not set (e.g. a reviewer running `docker compose
  up` with no secrets), the service falls back to a deterministic
  keyword-rule categorizer so the stack is fully runnable out of the box.
  This trade-off is documented in the README.
- **Git/GitHub**: repo initialized locally, commits made after each
  verified step (small, logical commits per the evaluation criteria).
  Pushed to a public GitHub repo named `task_20260818-1` under the
  `alukyanovich-hub` account (already authenticated via `gh`).
- **Category → description mapping** (used to sanity-check both the
  keyword fallback and the AI categorizer against the seed data):

  | Description template         | Expected category |
  |-------------------------------|--------------------|
  | Albert Heijn Purchase          | Groceries |
  | AH Online Groceries            | Groceries |
  | Bol.com Purchase                | Shopping |
  | Netflix Subscription            | Entertainment |
  | NS Train Ticket                 | Transportation |
  | Car Lease Payment               | Transportation |
  | Geldmaat ATM Withdrawal         | Miscellaneous |
  | Eneco Energy Bill               | Utilities |
  | Ziggo (internet/cable) Payment  | Utilities |
  | T-Mobile Bill Payment           | Utilities |
  | Municipal Tax Payment           | Housing |
  | Rent Payment                    | Housing |
  | Tax Refund                      | Miscellaneous |
  | Salary from Employer            | Miscellaneous (no "Income" category exists in the required 10) |
  | PayPal Transfer                 | Miscellaneous |
  | Bunq Transfer                   | Miscellaneous |
  | Transfer to ING Account         | Miscellaneous |
  | Payment to Rabobank             | Miscellaneous |
  | Payment to Credit Card          | Miscellaneous |
  | iDEAL Payment                   | Shopping |

## Step-by-step plan

### Step 1 — Bootstrap and verify
- Django project skeleton (`core` settings/urls, `apps/api/v1` router +
  drf-spectacular schema/swagger/redoc).
- Minimal `Dockerfile` + `docker-compose.yml` (web + postgres only).
- `.env.example` for config.
- Verify: `docker compose up` starts, migrations run, `/api/v1/schema/`
  and Django admin respond.

### Step 2 — Apps and models
- `transactions` app.
- `Category` as a `TextChoices` with the 10 required values.
- `Transaction` model: `external_id` (from CSV, unique, optional for
  API-submitted transactions), `amount`, `timestamp`, `description`,
  `transaction_type`, `account_number`, `category`, `category_source`
  (ai/rule-based/manual), `created_at`.
- Admin registration for manual inspection.
- Verify: migrations apply cleanly, admin list view works.

### Step 3 — Functionality
- `POST /api/v1/transactions/` — submit one transaction, categorised on
  save.
- `GET /api/v1/transactions/` — list, paginated, filterable by category.
- `GET /api/v1/transactions/{id}/` — detail.
- `POST /api/v1/transactions/import/` — multipart CSV upload matching the
  provided sample's columns, bulk-creates + categorises.
- Categorisation service: OpenAI-backed, prompt stored in
  `docs/AI_PROMPTS.md`, with description-level caching (many rows share
  an identical description, so we categorise each unique description once
  and reuse the result) and a keyword-rule fallback.
- Verify: manual API calls (curl) against a running stack.

### Step 4 — Seed data
- Convert `docs/transaction_history (3).xls` into a proper `.csv` fixture
  under `docs/` or `fixtures/`.
- Seed via the same `POST /transactions/import/` code path (either a
  management command calling it directly, or a curl/script) so the seed
  data proves the import endpoint works.
- Verify: category distribution looks sane against the mapping table
  above.

### Cross-cutting (after step 4)
- Unit + integration tests (model, categorizer fallback logic, API
  endpoints, CSV import edge cases).
- README: setup/run instructions, API reference, categorisation
  explanation + prompts, trade-offs, language/framework reasoning.
- `CLAUDE.md` for future coding-assistant context.

## Progress log

- **Step 1 (done)** — Django+DRF skeleton bootstrapped at repo root under
  `src/` (`core` project, `apps.api.v1` router with drf-spectacular
  schema/Swagger/Redoc). Trimmed `INSTALLED_APPS`/middleware to the
  minimum (no auth app, no Celery/Redis). `docker-compose.yml` needs zero
  configuration to run — every setting has a default baked in, `.env` is
  optional and only needed to set a real `OPENAI_API_KEY` or override
  DB credentials. Verified `docker compose up --build`: Postgres becomes
  healthy, Django migrations for the built-in apps apply, and
  `/admin/login/`, `/api/v1/schema/`, `/api/v1/doc/` all return 200.
- **Step 2 (done)** — `apps.transactions` app added with the `Transaction`
  model (`external_id` nullable+unique for dedup on CSV import,
  `category`/`category_source` blank until the categoriser runs) and
  `Category`/`TransactionType`/`CategorySource` as `TextChoices`.
  Registered in Django admin. Verified: `makemigrations` produced a
  single clean `0001_initial`, `migrate` applied it, and a shell-created
  `Transaction` round-trips correctly; admin site registry confirms the
  model is registered.
