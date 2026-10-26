# Tasks

## 1. Interrupt Of An Exited Leader

- [x] 1.1 Prove the race with regressions. A leader that exits between its poll and its interrupt leaves its group to the bounded close, both when the group then disappears and when a refusal lasts. A refusal while the leader still runs still fails cleanup. Done when the exited-leader cases fail against `57641887a` (the exited-leader cases failed against `57641887a`: `build/evidence/exited-leader-interrupt/red.log`).
- [x] 1.2 In the interrupt pass, record a refusal only while the leader still runs. Done when all three cases pass and the process adapter tests pass (all three cases pass, and the process adapter tests pass: `build/evidence/exited-leader-interrupt/related.log`).
- [x] 1.3 Record the fix under `[Unreleased]` in `CHANGELOG.md`. Done when the changelog validates (the `[Unreleased]` entry; `markdown_lint` and `prose` pass).

## Workflow follow-up

- Prove the exact head, archive this Change, then land with the lane's other Changes. The release owner cuts 0.2.0-alpha.16.
