# Tasks

## 1. Bound

- [x] 1.1 State the single-owner bound as a regression: every literal test-level timeout stays below the declared bound. Done when `tests/architecture/test_hang_bound.py` fails against the 120 s bound and the three 240 s marks (it named exactly those three marks).
- [x] 1.2 Declare one 600 s hang bound in `.config/checks/pytest/pytest.toml` and remove the three 240 s marks with their justifying comments. Done when the regression and the three formerly marked tests pass (22 passed with both affected modules).

## 2. Spec And Record

- [x] 2.1 Add the quality requirement that the per-test bound detects hangs. Done when strict validation passes and the simulated archive leaves every spec valid (12 specs valid after the simulated archive).
- [x] 2.2 Record the fix under `[Unreleased]` in `CHANGELOG.md`. Done when `markdown_lint` and `prose` pass.

## Workflow follow-up

- Archive, prove once, land and publish `dev` to GitHub. Then `stable-check-names` compensates its archive, refreshes onto this Change and proves once.
