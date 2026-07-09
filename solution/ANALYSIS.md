# Diagnosis — What is wrong with this project

This is the answer key for Part 1 of the workshop.
Participants should reach most of these conclusions on their own before reading this file.

---

## 1. Quality culture signals

- No `conftest.py` — no shared fixtures, no thought given to test isolation
- `pyproject.toml` lists only `requests` as a test dependency — no test framework beyond bare pytest
- Tests require a running app server and a live database with no documentation saying so
- `.github/workflows/ci.yml` has been written but will never pass in a fresh environment
- No coverage configuration, no coverage gate, no quality gates of any kind

---

## 2. Application code: what makes it hard to test

### `app/services/order_service.py`

| Problem | Line(s) | Impact |
|---|---|---|
| `OrderService.__init__` creates `PaymentClient()` and `EmailClient()` directly | `__init__` | Impossible to inject fakes without patching at the module level |
| `SessionLocal()` called inside every method | `create_order`, `cancel_order`, `calculate_order_total` | Cannot inject a test session; each call opens a real DB connection |
| `datetime.utcnow()` called inline | `create_order`, `cancel_order` | Cancellation-window logic can only be tested by sleeping 3600 s |
| `calculate_order_total` hits the DB to do arithmetic | `calculate_order_total` | A pure calculation requires a running PostgreSQL |

### `app/api/orders.py`

| Problem | Impact |
|---|---|
| `service = OrderService()` instantiated per request | No FastAPI `Depends()` injection point — can't swap the service in tests |

### `app/config.py`

| Problem | Impact |
|---|---|
| `PAYMENT_API_URL` hardcoded, ignores env | Tests always hit the real payment endpoint |
| `EMAIL_FROM` hardcoded | Cannot override email sender in tests |

---

## 3. Existing tests: catalogue of problems

### `tests/test_books.py`

| Problem | Where |
|---|---|
| Uses `requests` against `http://localhost:8000` | Every test — requires a live server |
| Global mutable `created_book_id = None` | Module level — tests must run in alphabetical/definition order |
| `test_get_book` crashes with `TypeError` if `test_create_book` never ran | `test_get_book` |
| `test_duplicate_isbn` leaves an orphan row in the DB | `test_duplicate_isbn` |
| No teardown — DB accumulates state across runs | Entire file |

### `tests/test_orders.py`

| Problem | Where |
|---|---|
| `setup_test_data()` called from multiple tests — creates duplicates, silently ignores 409 | `test_create_order_success`, `test_order_with_promo_code` |
| Direct `psycopg2` query — tests the DB, not the application | `test_order_reduces_stock` |
| `time.sleep(3700)` commented out — test always passes, never tests the deadline | `test_cancel_expired_order` |
| `if response.status_code != 201: return` — test lies green when the feature is broken | `test_order_with_promo_code` |
| `assert count > 0` — checks almost nothing | `test_db_state_after_tests` |
| `if not os.getenv("CHECK_DB_STATE"): return` — silently skips | `test_db_state_after_tests` |

### `tests/test_services.py`

| Problem | Where |
|---|---|
| `test_promo_code_save10` calls `calculate_order_total` which opens a real DB — not a unit test | `TestOrderServiceCalculation` |
| 80-line mock setup copy-pasted three times — no shared fixture | `test_create_order_calls_payment`, `test_create_order_sends_email` |
| Assertions only check call count, not correctness (`assert_called_once()`) | Both mock tests |
| `mock_query.first.side_effect = [mock_user, mock_book]` — fragile, order-dependent | Both mock tests |
| `assert service is not None` — tests nothing | `test_order_service_instantiation` |

---

## 4. CI: `.github/workflows/ci.yml`

| Problem | Impact |
|---|---|
| No dependency caching | Every run reinstalls all packages from scratch (~60-90 s wasted) |
| `pip install` instead of `uv sync` | Does not respect the lock file — builds may use different versions than local dev |
| No wait/health-check after `systemctl start postgresql` | Tests may start before the DB is ready (race condition) |
| App started with `&` but no health-check before `pytest` | Same race condition for the app server |
| `PAYMENT_API_KEY` secret required | CI fails on forks and first-time contributors; tests call the real payment API |
| No `DATABASE_URL` override | Uses the default from `config.py` — may conflict with CI's PostgreSQL setup |
| No coverage report or artifact | No visibility into what is actually tested |
| No test result artifact (JUnit XML) | GitHub cannot annotate failing lines in PRs |

---

## 5. Minimal refactoring plan

Only three changes are needed to make everything testable:

1. **`OrderService`** — accept `db`, `payment`, `email`, and `now` as constructor arguments
2. **`compute_total`** — extract as a pure function (no DB, no I/O)
3. **`api/orders.py`** — inject `OrderService` via `Depends()`

See `solution/order_service.py` for the result (~30 lines changed, zero logic altered).
