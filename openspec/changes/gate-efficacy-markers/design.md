# Design

## Context

Three committee rounds (scratch `gates-review/gate-efficacy-*`) settled the design. Under xdist,
only workers collect and run items, and the controller's session hooks cannot see worker
reports. Every worker collects the same suite, so a test that reads `request.session.items` sees
all of them. The proof's `unit-architecture` gate passes `tests`, which equals `testpaths`.

## Goals / Non-Goals

Goals: a gate's refusal, its conforming case and its failure behaviour are each proven by a named,
marked, non-skippable test. A credited proof cannot disappear silently.

Non-Goals:

- the `empty` role, which waits for per-gate `empty_selection`;
- planting new refusals for the weak and missing gates, which later slices do;
- a standing mutation floor (Phase T).

## Decisions

1. The plugin registers the marker in its `pytest_configure`, beside the semantics that give it
   meaning. Strict mode checks only a marker's name, so the plugin validates id and role during
   collection. It stores any error on the item and fails it from a
   tryfirst `pytest_runtest_setup`, because raising in a collection hook under xdist kills the
   controller.
2. A tryfirst `pytest_runtest_makereport` wrapper turns a skipped or xfailed marked item into a
   failure, clears `wasxfail`, and fails a non-strict XPASS. Each mark is added to
   `user_properties`.
3. The ledger is `CREDITED` in `test_gate_efficacy.py`. Its coverage check runs only on a
   whole-suite run: no item deselected, no `--lf`, no `--ignore`, and every `config.args` entry is
   a `testpaths` entry. A subset run asserts the ledger's own validity and skips the coverage
   comparison with its reason.
4. Credit needs one mutant. For each credited refusing pair, `tasks.md` records the policy element
   that was mutated, and the refusing test failing against it.

## Risks / Trade-offs

- Marking a test whose body later stops exercising its gate would keep a stale credit. The
  recorded mutant is the check; a standing mutation floor is Phase T work.
