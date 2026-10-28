# Proposal

## Why

ETHOS carries each capability once, so every consumer reaches the same owner (design revision 5.3,
D13). Two definitions repeat an owner that already serves every consumer:

1. `ethos hook pre-push` is a hidden CLI copy of Git's native pre-push hook. Both call
   `push_admission_report`. Only the copy adds the exact accepted-closeout command to its result, so
   the native hook that every push runs names a weaker next action than a command no journey uses.
2. `ethos.measure.effective_code_lines` reads one file and counts it. Every consumer counts source
   text through `effective_code_lines_for_source`.

## What Changes

- `push_admission_report` names the exact `ethos land --closeout` command when a push waits for
  accepted closeout. The native pre-push hook, the publication preview and the publish effect then
  report the same repair that `ethos status` and `ethos plan` name.
- The closeout command builder joins the other bounded recovery commands in
  `adapters/mutation/remediation/guidance.py`, which both the land reducers and push admission reach
  within the layer contract.
- `ethos hook pre-push`, its option fields and `measure.effective_code_lines` are removed. The tests
  that drove the CLI copy exercise the producer that the native hook calls.
- **CHANGELOG.** One entry under `[Unreleased]`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- None. No specification names the removed command, and the native pre-push admission requirements
  hold unchanged.

## Impact

- Python product code shrinks by 40 effective lines and tests by 67, measured with `ethos.measure`
  against `f699fa6cc`. The hook command group keeps `admit`, `commit-range`, `ref-update`,
  `ref-transaction`, `install` and `retire-supply`.
- No governed repository invokes the removed command or definition: a read-only search of the ten
  governed checkouts at their `HEAD` finds none.
- The layer contract stays kept: adapters reach the closeout command without importing the domain
  tier.
