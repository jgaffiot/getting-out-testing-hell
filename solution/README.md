# Solution — What Good Tests Look Like

This directory contains the refactored code and improved tests you'll build during the workshop.

## What changed

### Application code (minimal refactoring)
- `order_service.py` — dependency injection for `PaymentClient`, `EmailClient`, and the DB session; extracted pure `compute_total()` function; accepts a `now` parameter for time injection
- `api/orders.py` — uses FastAPI `Depends()` to inject `OrderService`

### Test infrastructure
- `conftest.py` — shared fixtures: real PostgreSQL via Testcontainers, FastAPI `TestClient`, pre-built factories
- `fakes.py` — in-process fakes for `PaymentClient` and `EmailClient`

### Test files
| File | What it covers | Technique |
|---|---|---|
| `test_books.py` | CRUD endpoints | TestClient + Testcontainers |
| `test_order_service.py` | Business logic | Unit tests, fakes, time injection |
| `test_orders_api.py` | Order flow E2E | TestClient + Testcontainers + fakes |
| `test_cancellation.py` | Time-sensitive logic | Injected `now` |

## Extra dependencies needed

```toml
[project.optional-dependencies]
test = [
    "pytest>=8.2",
    "pytest-cov>=5.0",
    "testcontainers[postgres]>=4.8",
    "httpx>=0.27",      # for TestClient async support
    "respx>=0.21",      # optional: HTTP-level mocking for PaymentClient
]
```
