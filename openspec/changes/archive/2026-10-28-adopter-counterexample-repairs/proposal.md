# Proposal

## Why

Three defects that only real adopters exposed refuse legitimate work in alphasim and di-effect (design revision 5.1, `product-architecture.md`, "Adopter counterexamples"). They are a 0.2.0 beta precondition: DR-0015 admits beta only with no known defect that blocks a landing or admits a wrong proof, and two of them refuse a landing and a repair.

1. **A moved configuration carrier is ambiguous.** A sole-file `lane format --check` of `.config/checks/taplo/taplo.toml` refuses `native_tool_configuration_ambiguous:taplo`. The index still lists the previous carrier that the worktree deleted, and carrier selection counts it.
2. **A release command does not own its executable.** A prewrite that references `pixi` is refused with `product_reference_not_admitted_at_baseline:executable:pixi`, although `.ethos/release.toml` invokes it in `local_verification_command`. The accepted requirement "Native command declarations own their executables" says release command fields own executables; the reader ignores them.
3. **Another Change's template drift holds a validation repair.** A one-file repair that restores strict validity of di-effect's `pre-push-git-env-isolation` is refused by its own preimage. Two other active Changes' template drift sits beside its validation failure, and the validation-repair context admits no other gap. Template repair already lets two drifted Changes repair independently; validation repair does not.

The receipt for the second row also refused `value:ALPHASIMDMGR_IN_DOCKER_GATE`. That refusal was correct at its baseline, where the value had no declaration; the adopter declared it later in `system/surfaces.toml`, which the reader already reads.

## What Changes

- Native configuration selection counts only carriers present in the worktree. Two present carriers still refuse.
- The release declaration's local publication commands own the executables they invoke.
- An active Change's validation repair is admitted beside another active Change's template drift. Its own drift and any other gap still keep the repair closed, and the other Change's drift stays reported.
- The repository-governance scenario "Official validation requires an active Change artifact repair" states that rule.
- **CHANGELOG.** One entry under `[Unreleased]`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: an active Change's validation repair is admitted beside another active Change's template drift.

## Impact

- Python product code shrinks by 11 effective lines. Each repair is paid for inside its own owner: carrier selection folds into the existing check, command declarations get one selector, and the two OpenSpec repair contexts share one check for the complete selected Change. The release publication module makes its local command field names public.
- The regressions replay each receipt's exact condition in `tests/unit`.
- alphasim and di-effect are not changed. Their owners can retry the refused operations once a release carries this Change. The final shapes stay with `verification-throughput`, `reference-observation-repair` and `change-selection`.
