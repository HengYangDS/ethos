# Design

## Context

See the [proposal](proposal.md). The gate compares function bodies after renaming the names they
bind and keeps the names they read; bodies under four syntax nodes are idioms and are ignored.

## Goals / Non-Goals

Goals:

- No two identical function bodies across `src/`, `tools/` and `tests/`.
- Each shared test behavior has one owner, placed nearest its users.

Non-Goals:

- Near-copies the gate does not report: inline custody paths in two tests, inline runtime
  executable paths in `src/` and the fixture Python, and two duplicated ceiling constants. Each
  needs its own owner decision.
- The fixture construction authority, which Phase T item 1 owns.

## Decisions

1. **Placement.** A fixture that modules of one directory share moves to that directory's
   `conftest.py`; a helper that several directories use moves to `tests/support`; an existing owner
   is reused before a new one is written.
2. **Parametrized tests.** For a `test_` function the decorators join the shape, unrenamed, since
   they read names of the enclosing scope. A planted case groups two identically decorated tests
   and keeps a differently parametrized one apart.
3. **Product owner.** The executable path inside a virtual environment is computed by product,
   tools and test support alike, so `runtime_executable` sits beside `runtime_scripts` in the
   runtime filesystem module and the other two import it. The journey test's digest copy becomes
   expected data: an oracle, not a second implementation.
4. **Assertions keep their meaning.** One counter becomes a list (`len(synchronized) == 2`) and
   one lambda renames its unused parameters; no other assertion or docstring changes.

## Risks / Trade-offs

- Shared support modules gained functions; the lane's impacted sweep runs their other importers.
- Failures seen only in the scratch clone (no `.venv`, a stale runtime build, a symlinked
  `node_modules`) are checked again in the lane.
