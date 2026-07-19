# Budget Contract v2 Foundation Integration Continuation

## Why

The Budget Contract v2 Foundation is officially archived and historically
proved, but its successor could not land after `candidate/dev` advanced: land
reported `candidate_base_stale`, and the official refresh encountered a real
semantic conflict, failed closed as `refresh_base_failed`, and restored the old
Lane clean. A current-candidate continuation is required to preserve the useful
history, regenerate current evidence, and correct reviewed facts without
rewriting the historical archive.

## What Changes

- Require semantic refresh conflicts to abort and restore the predecessor Lane
  rather than permitting manual rebase continuation or skipped commits.
- Start an owned successor from the latest candidate, bind the same episode
  claim, and keep predecessor Lanes and archived carriers observe-only.
- Preserve history through a no-fast-forward merge whose first parent is the
  successor candidate base and whose second parent is the absorbed predecessor
  head; repeat this successor step if the candidate advances again before land.
- Retain candidate-authoritative configuration, gate, and parity projections,
  then regenerate parity and execute proof for the resulting current HEAD.
- Supersede the Foundation replay statement with the independently reproduced
  `105060` / `-282 ELOC` result and align the extraction plan with the actual
  declarative taxonomy and explicit `state_mode = "advisory_gaps"` provider.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: subject=archived-work-lane-candidate-drift-continuation;
  reuse=extend; change=modify;
  facet:lifecycle=authoring,validation,proof,archive,closeout;
  facet:surface=work-lane,openspec,claim,evidence,parity;
  facet:authority=source,test,openspec,claim,evidence.

## Impact

This continuation changes the Budget Contract v2 plans, the active episode
claim and Chronicle, the OpenSpec repository-governance contract, parity
evidence, and Work Lane ancestry. It does not change the Foundation's v1 source
budget behavior or implement later Budget Contract v2 tasks.

## Out Of Scope

- Tasks 2 through 10 of the Budget Contract v2 implementation plan.
- v2 enforcement, calibration, cutover, v1 global LOC retirement, or terminal
  compression settlement.
- Mutation of historical archives, historical Chronicles, proof receipts,
  foreign Work Lanes, or protected roots outside native closeout commands.
- Remote push, remote publication, or hosted CI claims.
