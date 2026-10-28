# Tasks

## 1. Repairs

- [x] 1.1 Select native configuration carriers only among paths present in the worktree. Done when the moved-carrier regression passes and two present carriers still refuse (`tests/unit/adapters/gates/test_native_inputs.py`).
- [x] 1.2 Make the release declaration's local publication commands own the executables they invoke. Done when the release-command regression passes and an undeclared executable stays absent (`tests/unit/repository/policy/references/test_native_package_declarations.py`).
- [x] 1.3 Admit an active Change's validation repair beside another active Change's template drift. Done when the repair regression passes for another Change's drift and still refuses the selected Change's own drift and any other gap (`tests/unit/admission/current/test_repair.py`).

## 2. Spec And Record

- [x] 2.1 Restate the repository-governance scenario "Official validation requires an active Change artifact repair" with the coexistence rule. Done when strict validation passes and the simulated archive leaves every spec valid (12 specs valid after the simulated archive: build/evidence/adopter-counterexample-repairs/archive-simulation.log).
- [x] 2.2 Record the repairs under `[Unreleased]` in `CHANGELOG.md`. Done when `markdown_lint` and `prose` pass.

## Workflow follow-up

- Prove the exact head, archive this Change, prove the archived head, land it and publish `dev` to GitHub.
- After a release carries this Change, tell the alphasim and di-effect owners which refused operations to retry.
