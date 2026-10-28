# Tasks

## 1. Observation

- [x] 1.1 Resolve Python executor and environment reads through import bindings, lexical scope and program point, and delete owner spelling and the command-name rule. Done when the binding regressions pass for aliases, shadowing, scope, program point and caller-supplied values (`tests/unit/repository/policy/test_reference_bindings.py`).
- [x] 1.2 Make a carrier UNKNOWN when a sink is chosen by dynamic lookup. Done when its regression keeps the carrier's static references and leaves unrelated files evaluated.
- [x] 1.3 Read Dockerfile `ENV` and `ARG` names and Compose service environments as declared values. Done when the container regressions pass for both Dockerfile forms, `ARG`, and both Compose forms, and a `RUN` command observes no executable.
- [x] 1.4 Move product-surface enumeration to `repository/policy/surfaces.py`. Done when no reference module imports `repository.policy.boundary` and the tier-edge measurement drops by that one edge.

## 2. Spec, Documents And Record

- [x] 2.1 Restate the repository-governance binding requirement and add the container environment requirement. Done when strict validation passes and the simulated archive leaves every spec valid.
- [x] 2.2 State the repaired observer in the plan's convergence item and the semantics research note. Done when `markdown_lint` and `prose` pass.
- [x] 2.3 Record the repair under `[Unreleased]` in `CHANGELOG.md`. Done when `markdown_lint` and `prose` pass.

## Workflow follow-up

- Rebase onto accepted `dev` after `surface-pruning` lands, measure `python_product` there, archive, prove once, land and publish `dev` to GitHub.
- After a release carries this Change, tell the alphasim and di-effect owners to retry the refused prewrite, confirm `ethos-introduction-film` declares `ffmpeg`, and record the installed acceptance of task 10.11.
