# Tasks

## 1. Retention Observes Consumers

- [x] 1.1 Prove the write with a regression: retention of an installation recorded by a repository
  without ETHOS state creates nothing in that repository and retires the installation. Done when the
  test fails against `bb242fd35` (retention created `ethos/` in the plain repository:
  `build/evidence/retention-observes-consumers/red.log`).
- [x] 1.2 Take a consumer's selection lock only when its `ethos/` directory exists. Done when the
  host-retention, legacy-supply and selection tests pass and `python_product` grows by at most 2
  lines (579 passed across the 25 test modules that run retention or hook installation,
  `green.log`; `host_retention.py` grows by 1 effective line).
- [ ] 1.3 State in the `[Unreleased]` fix note of `CHANGELOG.md` that retention creates nothing in a
  repository without ETHOS state. Done when `markdown_lint` and `prose` pass with the other fast
  gates.

## Workflow follow-up

- Archive this Change and prove the archived head once. After landing, the release Change refreshes
  the 0.2.0-alpha.18 entry at the landed head once hosted Windows host conformance passes there.
