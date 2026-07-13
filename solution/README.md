# Solution — What Good Tests Look Like

This directory contains the refactored code and improved tests you'll build during the workshop.

## What changed

### Application code (minimal refactoring)
- `order_service.py` — dependency injection for `PaymentClient`, `EmailClient`, and the DB session; extracted pure `compute_total()` function; accepts a `now` parameter for time injection
- `api_orders.py` — refactored router that uses FastAPI `Depends()` to inject `OrderService`, `PaymentClient` and `EmailClient`

### Test infrastructure
- `tests/conftest.py` — shared fixtures: real PostgreSQL via Testcontainers, FastAPI `TestClient`, in-process fakes, data factories
- `fakes.py` — in-process fakes for `PaymentClient` and `EmailClient`

### Test files
| File | What it covers | Technique |
|---|---|---|
| `tests/test_books.py` | CRUD endpoints | TestClient + Testcontainers |
| `tests/test_order_service.py` | `compute_total` + `create_order` business logic | Unit tests, fakes |
| `tests/test_cancellation.py` | The 1-hour cancellation window | Service-level tests with injected `now` |
| `tests/test_orders_api.py` | Order flow end-to-end | TestClient + Testcontainers + fakes (via the refactored router) |

## Running the solution tests

```bash
uv sync --group solution
uv run pytest solution/tests/ -v
```

The `solution` group is defined in `pyproject.toml` and bundles everything the reference tests need:

```toml
[project.optional-dependencies]
solution = [
    "pytest>=8.2",
    "pytest-cov>=5.0",
    "testcontainers[postgres]>=4.8",
    "respx>=0.21",
]
```

> Requires a working Docker/Podman daemon for Testcontainers.
