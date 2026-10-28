# Tasks

## 1. One Proof

- [x] 1.1 Admit an archive of a completed Change at the exact Work Lane head without a pre-archive proof, and name the post-archive proof report `pending_verification`. Done when the docs-only archive regression commits once without a prior proof and continues with the archived head's proof (`tests/unit/openspec/lifecycle/test_archive_task_completion.py`).
- [x] 1.2 Compensate an unlanded archive with `lane archive-change --compensate`. Done when the compensation regressions return the lane, index and worktree to the pre-archive head, refuse an inexact or landed archive without an effect, and complete an interrupted run (`tests/unit/lanes/lifecycle/archive/test_compensation.py`).
- [x] 1.3 Retire the proof execution carrier and `prove --execution-root`. Done when no product, test or document references the carrier and the proof and archive suites pass.

## 2. Spec And Documents

- [x] 2.1 Restate the repository-governance archive requirements, add compensation and remove the two carrier requirements. Done when strict validation passes and the simulated archive leaves every spec valid (12 specs valid after the simulated archive).
- [x] 2.2 State the one-proof route in `runner-and-mutation.md`, `command-plane.md`, the release guide and the governance Skill map, and correct the runner name and the proof-copy paragraph in `runner-and-mutation.md`. Done when `markdown_lint`, `prose` and the Skill package checks pass.
- [x] 2.3 Record the route under `[Unreleased]` in `CHANGELOG.md`. Done when `markdown_lint` and `prose` pass.

## Workflow follow-up

- Archive this Change with its own lane code, prove the archived head once, land it and publish `dev` to GitHub.
- Ship it in the next release, so that adopters' installed runtimes use the one-proof route.
