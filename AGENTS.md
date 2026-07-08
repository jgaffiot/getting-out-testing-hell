# Repo purpose

This is workshop material — *"Getting out of the testing hell"* — for intermediate
Python developers. Participants are handed a FastAPI + PostgreSQL bookstore app with
deliberately bad tests and a testable-but-not-tested architecture, and their job during
the workshop is to diagnose the problems and fix them themselves (see `README.md` and
`ABSTRACT.md` for the full brief).

## Layout

- `app/`, `tests/`, `.github/workflows/ci.yml` (root) — the **workshop starting point**.
  Intentionally flawed: brittle/order-dependent tests, un-injectable dependencies, a
  broken CI pipeline. This is what participants work on.
- `solution/` — the **reference solution**: refactored app code and rewritten tests
  showing one valid end-state (dependency injection, Testcontainers, fakes, fixed CI).
  It exists as an answer key participants can compare against *after* attempting the
  exercise themselves, per `solution/README.md`.

## Important: don't spoil the workshop

If you're helping someone who is doing (or facilitating) this workshop — diagnosing
`tests/`, refactoring `app/`, writing new tests, fixing the root CI — **do not reach
into `solution/` to solve it for them.** Don't copy code from `solution/`, don't paste
its fixtures/fakes/services into the root `app/`/`tests/`, and don't reveal its
contents unprompted. The value of the workshop is in participants finding the seams
and design themselves.

It's fine to:
- Discuss `solution/` explicitly if the user asks to see it, compare against it, or
  says they're past the exercise / just reviewing the answer key.
- Work on `solution/` directly when asked to (e.g. this session's CI caching change).
- Point out that a reference solution exists, without detailing its contents.

When in doubt about which mode you're in (doing the exercise vs. maintaining the
answer key), ask.
