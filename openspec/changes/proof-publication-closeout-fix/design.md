# Design

`openspec_status_result()` deliberately returns an empty mapping when no Change
is selected. All downstream optional consumers already use `.get`; the lifecycle
projection was the sole unconditional index. It now receives the same empty
payload without manufacturing a status command or weakening active-Change
contracts.

## Requirement to proof

| Requirement | Proof |
| --- | --- |
| Empty official Change list is valid | `test_governance_accepts_an_empty_official_change_list` |
| Active Change status remains strict | Existing governance report matrix |
| Package-only accepted proof closes | Exact-HEAD post-land full proof |

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| `repository-governance:accepted proof without active Change` | `1.3` | `test_governance_accepts_an_empty_official_change_list` |
