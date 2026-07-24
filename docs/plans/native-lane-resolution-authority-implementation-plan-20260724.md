---
subject: ethos:native-lane-resolution-authority-implementation-plan-20260724
role: plan
state: active
relations:
  implements: native-lane-resolution-authority-design-20260724
---

# Native Lane Resolution Authority Implementation Plan

Status: active.

Purpose: execute the approved native lane-resolution authority cut through
test-first implementation, proof, archive, land, closeout, and bounded
housekeeping.

See also: [Design](native-lane-resolution-authority-design-20260724.md),
[Product Design Contract](../governance/product-design-contract.md), and
[Command Plane](../reference/command-plane.md).

> **For agentic workers:** execute every task test-first, verify the intended RED
> before production edits, and review each independently testable slice before
> continuing.

**Goal:** Replace split ownerless-retirement authority with a self-contained,
provider-neutral ETHOS implementation and close the complete governance,
evidence, landing, and housekeeping lifecycle.

**Architecture:** Perform a single non-destructive authority cut to a new current
record root. Add native admission over existing repository/Git/state facts, then
reuse the proven fence, reservation, recovery, CAS, postcondition, and cleanup
mechanisms. Historical roots remain opaque and immutable.

**Tech stack:** Python 3.14, Pydantic contracts, JSON Schema 2020-12, SQLite,
Git plumbing, pytest, Ruff, ty, OpenSpec 1.6, ETHOS lifecycle commands.

## Global constraints

- All tracked writes stay in `work/20260724-native-lane-resolution-authority`
  after exact `ethos lane prewrite` admission.
- Every `__init__.py` contains only a docstring.
- Import every symbol from its defining module; no facade, barrel, alias,
  `__getattr__`, compatibility layer, or single-implementation Protocol.
- Current readers and writers use only
  `<accepted>-records/recovery/lane-resolution-v2/`.
- Predecessor records remain byte-preserved in place and never authorize current
  effect, conflict resolution, recovery, or clear.
- No production code may precede its focused failing regression test.
- No real foreign lane is retired during effect acceptance.
- Remote publication is not authorized.

## Task 1: Carrier and baseline

**Files:** the active OpenSpec Change, its scope, this design and plan, the new
Claim and Chronicle, and the predecessor Claim.

1. Run strict lifecycle before implementation and retain the exact gaps.
2. Validate that current inventory has zero inflight/partial records, the fence
   table is empty, and no reservation sidecar exists.
3. Supersede the predecessor Claim and bind the successor Claim to existing
   carrier and design paths only.
4. Run `openspec validate native-lane-resolution-authority --strict --json`,
   `tools/ci/scripts/run-ethos-lane.sh openspec --lifecycle --json`, and
   `tools/ci/scripts/run-ethos-lane.sh quality claims --json`.

## Task 2: Record roots and inventory

**Tests:**

- `tests/unit/lanes/test_lane_resolution_artifacts.py`
- `tests/unit/coverage/test_lane_resolution_record_edges.py`
- `tests/unit/cli/test_contracts_lane_resolution.py`

**Production:**

- create `resolution/records/roots.py`;
- modify current receipt, release, recovery, cleanup, and inventory readers;
- remove the ambiguous multi-root helper.

Write and observe failing tests for current/history isolation, decision-only
inventory, and invalid current payloads. Implement `current_record_root()` and
`historical_record_roots()`, change the identifier union to include decisions,
and expose `decision_count`, `pending_decision_count`,
`invalid_current_record_count`, and `decision_pending`. Run the three focused
files until green, then run module-layout and no-compat gates.

## Task 3: Typed receipt, reservation, and clear records

**Tests:**

- `tests/unit/kernel/test_lane_resolution_contract.py`
- `tests/unit/lanes/retirement/test_ownerless_closeout_receipt_edges.py`
- `tests/unit/lanes/retirement/test_ownerless_closeout_recovery.py`
- `tests/unit/kernel/test_ownerless_state_final_edges.py`

**Production:**

- create `ethos_core/contracts/resolution/closeout.py`;
- create `resolution/records/reservations.py`;
- modify receipt/clear schemas, `records/core.py`, state fencing, effect, retry,
  recovery, and cleanup.

First make tests fail on the old version and provider-prefixed fields. Add the
closed version-3 receipt binding, version-2 reservation model, version-1 clear
receipt, and exact 40/64 Git OID constraints. Delegate reservation persistence
to the typed model and remove duplicate handwritten shape validation. Preserve
phase and recovery-state matrices. Run focused tests, schema validation, types,
code-size, module-layout, and no-compat.

## Task 4: Native admission and effect reconnection

**Tests:**

- `tests/unit/lanes/retirement/test_ownerless_closeout_admission.py`
- `tests/unit/lanes/retirement/test_ownerless_closeout_effect.py`
- `tests/unit/lanes/retirement/test_ownerless_closeout_fence.py`
- `tests/unit/lanes/retirement/test_ownerless_no_effect_retry.py`
- `tests/unit/lanes/retirement/test_ownerless_cleanup_recovery.py`

**Production:**

- create `resolution/closeout/admission.py`;
- modify `_effects.py`, effect, retry, recovery, cleanup, observation, and Git
  ancestry helpers;
- delete the retired adapter package and its response-edge test file.

Add failing cases for decision and Chronicle drift, custom Work Lane role,
registration/path/HEAD/incarnation drift, dirty state, holder/lease/Claim,
accepted ancestry, competing fence, and post-fence drift. Implement native
preflight and a complete post-fence re-observation, then feed the resulting
provider-neutral binding into the existing reservation and CAS path. Run the
focused state-machine, crash/retry, Git CAS, and three-state suites until green.

## Task 5: Configured role and generic coupling

**Tests:** native-admission custom-prefix tests plus governance coupling tests
under `tests/unit/governance` and `tests/architecture`.

Add a failing custom-prefix admission fixture before implementation and consume
the existing `work_branch_prefix` role policy without renaming keys or changing
lane-start behavior. Extend coupling audit to
discover mandatory lifecycle command execution and fail when the binding is not
declared. Declare only Git and ETHOS-native state/schema bindings for Work Lane
lifecycle. Confirm optional unrelated adapters remain valid.

## Task 6: Current truth and zero residue

Update the canonical requirement, command reference, predecessor plans, archived
carrier, predecessor Claim/Chronicle, schemas, source comments, and tests using
neutral repository-role vocabulary. Keep permanent prevention provider-neutral:
contract fields cannot promote adapter-specific authority and mandatory
lifecycle executables must be declared by the coupling registry. Use a one-time
closeout scan to prove the retired token is absent from the current tracked tree;
do not add that token to any tracked blacklist, constant, or test. Recompute
Chronicle digests and validate Claims.

## Task 7: Full proof and archive

Run, at minimum:

```bash
tools/ci/scripts/run-python-lint.sh
tools/ci/scripts/run-python-tests.sh
tools/ci/scripts/run-config-lint.sh
tools/ci/scripts/run-shell-lint.sh
tools/ci/scripts/run-module-layout.sh
tools/ci/scripts/run-no-compat.sh
tools/ci/scripts/run-import-linter.sh
tools/ci/scripts/run-ethos-lane.sh quality types --json
tools/ci/scripts/run-ethos-lane.sh quality schemas --json
tools/ci/scripts/run-ethos-lane.sh quality code-size --json
tools/ci/scripts/run-ethos-lane.sh quality coupling-audit --json
tools/ci/scripts/run-ethos-lane.sh quality claims --json
tools/ci/scripts/run-ethos-lane.sh openspec --lifecycle --json
```

Execute generic shadow parity in the admitted lane, commit the result, then run
`ethos prove --execute --expect-head "$(git rev-parse HEAD)" --json`. Complete
the task checklist and Chronicle only after fresh evidence exists. Officially
archive the Change, move the Claim carrier to the dated archive, commit, and
rerun exact-HEAD proof.

## Task 8: Land, closeout, and housekeeping

Land the exact proven HEAD to candidate, then perform accepted-root closeout as
a separate audited transition. Run `ethos publish --json` only as a local
readiness check. Retire the landed successor and the two task-owned predecessor
mistake lanes using native exact closeout; if ancestry/absorption is unprovable,
create a Chronicle-bound preserve-retire decision instead of inventing
supersession evidence. Remove only task scratch, caches, bytecode, and abandoned
temporary proof artifacts. Finish with clean accepted/candidate roots, no live
task-owned lease, no task-owned registered worktree, and unchanged predecessor
local records.
