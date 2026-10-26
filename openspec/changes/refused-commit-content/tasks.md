# Tasks

## 1. A Refused Commit Keeps Its Content

- [x] 1.1 Prove the loss with two regressions. A policy-refused direct commit to `dev` keeps its staged change, and its refusal names the refused commit. Compensation keeps the checkout for a target that no ref contains. Done when both fail against `3764e94c1` (both regressions failed against `3764e94c1`: `build/evidence/refused-commit-content/red.log`).
- [x] 1.2 Compensate only a target that another ref contains. Otherwise keep the index and worktree, and report the target. Done when both regressions pass and the existing merge, checkout and overlay compensation tests still pass (both pass; the hook runtime suite and 18 related test files pass).
- [x] 1.3 Record the fix under `[Unreleased]` in `CHANGELOG.md`. Done when the changelog validates (the `[Unreleased]` entry; `markdown_lint` and `prose` pass).

## Workflow follow-up

- Prove the exact head, archive this Change, prove the archived head, then land, close out and re-arm the root. No publication.
- The release owner cuts 0.2.0-alpha.16 from the landing.
