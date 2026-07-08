# Getting Out of the Testing Hell

Workshop material — *Getting out of the testing hell!*

---

## The application

A bookstore REST API built with FastAPI + PostgreSQL. It supports:

- **Books** — CRUD catalog with stock levels
- **Users** — basic accounts
- **Orders** — place an order, pay with a card token, get an email confirmation, cancel within 1 hour

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

### Run the existing tests

```bash
uv sync --extra test
uv run pytest tests/ -v
```

> **Warning:** most tests require a running app **and** a running database.
> Several will fail or silently skip without the right environment.

---

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
