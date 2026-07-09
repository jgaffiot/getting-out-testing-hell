# Getting Out of the Testing Hell

Workshop material — *Getting out of the testing hell!*

---

## The application

A bookstore REST API built with FastAPI + PostgreSQL. It supports:

- **Books** — CRUD catalog with stock levels
- **Users** — basic accounts
- **Orders** — place an order, pay with a card token, get an email confirmation, cancel within 1 hour

<details>
<summary>Current architecture (<code>app/</code>)</summary>

```
app/
├── main.py               # FastAPI app, wires the 3 routers together
├── config.py              # module-level constants, part env var / part hardcoded
├── database.py             # engine, SessionLocal, Base, get_db() dependency
├── models/                  # SQLAlchemy ORM: Book, User, Order, OrderItem
├── schemas/                  # Pydantic request/response schemas
├── api/                        # FastAPI routers: books, users, orders
├── services/
│   └── order_service.py        # OrderService: order placement & cancellation logic
└── clients/
    ├── payment_client.py        # PaymentClient - real HTTP calls (httpx) to a fake payment API
    └── email_client.py          # EmailClient - real SMTP calls (smtplib)
```

- `books` and `users` routers talk directly to the DB via the `get_db()` FastAPI dependency
  — thin CRUD, no service layer.
- `orders` router delegates to `OrderService`, but builds a **new `OrderService()` per
  request** rather than receiving one via `Depends()`.
- `OrderService.__init__` builds its own `PaymentClient()` and `EmailClient()`, and
  `create_order()` / `cancel_order()` each open their own `SessionLocal()` session
  directly instead of reusing the request's DB session — none of the three collaborators
  (DB session, payment client, email client) are injectable.
- `PaymentClient.charge/refund` and `EmailClient.send` make real outbound calls
  (`httpx.post` to `PAYMENT_API_URL`, `smtplib.SMTP` to `EMAIL_SMTP_HOST`) — there's no
  fake/stub seam, so exercising `OrderService` means hitting (or mocking) real network calls.
- Order total/promo calculation lives inline inside `create_order` (and is duplicated,
  slightly differently, in the otherwise-unused `calculate_order_total`) — pure
  arithmetic is mixed with DB reads and I/O.
- Time is read via `datetime.utcnow()` inline in `create_order` / `cancel_order` — the
  1-hour cancellation window can't be exercised without actually waiting.
- `config.py` mixes `os.environ.get(...)` values with hardcoded constants
  (`PAYMENT_API_URL`, `EMAIL_FROM`) read once at import time.

</details>

## Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (required)
- Docker or Podman (recommended, for the database)

### Start the infrastructure

```bash
docker compose up -d
```

### Install dependencies & run the app

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

API docs available at <http://localhost:8000/docs>.

### Run linters

```bash
uv run ruff format .
uv run ruff check .
uv run ty check .
```

By default, a small set of Ruff rules are activated.

The solution passes Ruff with almost all rules :

```bash
uv run ruff check --select ALL --ignore EM,TRY003 solution/app
uv run ruff check --select ALL --ignore EM,TRY003,S,ANN,PLR2004 solution/test
```

### Run the existing tests

```bash
uv sync --group test
uv run pytest tests/ -v
```

> **Warning:** most tests require a running app **and** a running database.
> Several will fail or silently skip without the right environment.

### Run the solution

Requires non-root container: Podman, rootless Docker, or belonging to the 'docker' group

> **Warning:** belonging to the 'docker' group is effectively equivalent to being root, because
> anyone in the docker group can mount the filesystem root ('/') into a privileged container.

```bash
uv sync --group solution
uv run pytest tests/ -v
```

In case of problems with Podman, try:

```bash
# Enable the rootless Podman socket
systemctl --user enable --now podman.socket
# Point testcontainers at it:
export DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock
```

and in case of test crash with a `docker.error`, try:

```bash
export TESTCONTAINERS_RYUK_DISABLED=true
export TESTCONTAINERS_HOST_OVERRIDE=localhost
```

## Workshop structure

### Part 1: Diagnosis (guided analysis, 45 minutes)

* Intro & setup check (10 minutes)
* Exploring the codebase and run the tests (15 minutes)
  1. **Quality culture** — what signals do you see in the repo about how testing is valued?
  2. **Architecture** — what makes the code hard to test? Where are the seams? what are the core services, 
    the 3-rd party services, and the contract between them?
  3. **Existing tests** — list every problem you find in `tests/`. How many tests actually test something?
  4. **CI** — what is wrong with `.github/workflows/ci.yml`?
* Guided diagnosis, why the tests are bad (20 minutes)

### Part 2 : Strategy (guided analysis + group work, 40 minutes)

* Some concepts and vocabulary (5 minutes)
* Defining a test strategy (20 minutes)
* Discussing trade-offs (5 minutes)
* Tooling introduction (10 minutes)

10-minutes break

### Part 3 : Implementation (hands-on coding, 75 minutes)

* Fix existing tests (20 minutes)
* Add new tests (25 minutes)
* Minimal refactoring (15 minutes)
* CI setup (10 minutes)

### Conclusion (10 minutes)

* Review the end-result (8 minutes)
* Ressources (2 minutes)

---

## Hints

<details>
<summary>Problems in the existing tests (spoilers)</summary>

- Tests call a live HTTP server (`requests.get("http://localhost:8000/...")`) — not portable, order-dependent
- Global mutable state (`created_book_id = None`) — tests must run in alphabetical order
- `setup_test_data()` is called multiple times without cleanup — leaves garbage in the DB
- Direct `psycopg2` calls bypass the API — tests the DB, not the app
- `time.sleep(3700)` is commented out — the test always passes, never tests the deadline
- Silent `return` on failure — tests lie green when the feature is broken
- Mocks that only verify call count, not correctness
- No teardown anywhere

</details>

<details>
<summary>Problems in the application code (spoilers)</summary>

- `OrderService.__init__` creates `PaymentClient()` and `EmailClient()` directly — no way to inject fakes
- `OrderService` calls `SessionLocal()` itself — can't inject a test session
- `datetime.utcnow()` called inline — time-dependent logic can't be tested without sleeping
- `calculate_order_total` hits the DB to do arithmetic — pure logic buried in I/O
- API router instantiates `OrderService()` per request — no injection point

</details>

<details>
<summary>Minimal refactoring needed</summary>

- Add constructor parameters: `OrderService(db, payment, email, now=datetime.utcnow)`
- Extract `compute_total(prices, promo_code)` as a pure function
- Use FastAPI `Depends()` to inject `OrderService` into the router

See `solution/order_service.py` for the result.

</details>

---

## Reference solution

`solution/` contains the refactored service and improved tests.
See `solution/README.md` for a full explanation of what changed and why.

<details>
<summary>Test design choices (<code>solution/tests/</code>)</summary>

**Fixture scoping** (`conftest.py`) — three layers, chosen to pay the expensive setup
once while still keeping tests isolated from each other:

- `pg_container` (**session**-scoped) — one real PostgreSQL container for the whole test
  run. Starting a container per test would dominate the run time.
- `db_engine` (**session**-scoped) — one SQLAlchemy engine against that container, with
  the schema created once via `Base.metadata.create_all()`.
- `db` (**function**-scoped, the default) — each test gets its own connection wrapped in
  a transaction that is rolled back on teardown. Tests can freely insert/mutate rows
  without cleaning up or polluting the next test, without needing a fresh container.

**Testcontainers** — `testcontainers[postgres]` spins up a real `postgres:18` in
Docker/Podman rather than SQLite or a mocked session. The app relies on Postgres-specific
behavior (`Numeric` for money, a native `Enum` for `OrderStatus`) that an in-memory or
different-engine DB wouldn't faithfully exercise.

**Fakes over mocks** (`fakes.py`) — `FakePaymentClient` and `FakeEmailClient` are small,
working in-memory implementations, not `unittest.mock.Mock`:

- `FakePaymentClient` records real `FakeCharge` objects in `self.charges`, generates
  incrementing charge ids, and can be built with `fail_on_token=...` to simulate a
  declined card — so `cancel_order`'s refund logic, for instance, can be asserted against
  `payment.charges[0].refunded is True` instead of just checking `refund.assert_called()`.
- `FakeEmailClient` records `SentEmail` objects, so tests assert on the actual recipient/
  subject/body rather than only "send was called".

This is deliberately different from `_check_connections` (see `order_service.py`), which
is patched with a plain `unittest.mock.MagicMock` via the autouse `no_connection_check`
fixture — that method is infrastructure noise (a random sleep unrelated to business
logic), so there's nothing worth faking; it's stubbed out entirely. Fakes are reserved for
collaborators (`payment`, `email`) whose behavior the tests actually care about.

</details>
