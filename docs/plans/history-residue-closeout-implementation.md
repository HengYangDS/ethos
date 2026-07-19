---
subject: ethos:history-residue-closeout-implementation-20260719
role: plan
state: active
relations:
  implements: history-residue-closeout-20260719
  derives_from: docs/plans/history-residue-closeout-design.md
---

# History Residue Closeout Implementation Plan

Status: active.

Purpose: execute the tracked, local-state, recovery, and source-budget cleanup
defined by the history-residue closeout design.

See also: [OpenSpec change](../../openspec/changes/history-residue-closeout-20260719/)
and the [design](history-residue-closeout-design.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove unreasonable tracked and local `.ethos` history residue while preserving active governance, recovery, and proof boundaries and closing all debt expired on July 18, 2026 through measured deletion.

**Architecture:** Tracked configuration is repaired together with adopter scaffolds; local state is maintained only by an explicit digest-bound action; optional provider executables retire while their contracts remain; source-budget debt closes only after category metrics prove the allowances unnecessary.

**Tech Stack:** Python 3.14, pytest, Cyclopts, SQLite, TOML, Jinja, Git, OpenSpec 1.6.0, ETHOS Work Lane lifecycle.

## Global Constraints

- Work only in the owned Work Lane root resolved by Git, with
  `ETHOS_ACTOR=agent:openai:thread:root` and `ETHOS_ROOT="$PWD"` explicitly bound.
- Run `tools/ci/scripts/run-ethos-lane.sh lane prewrite ... --editor-root "$PWD" --require-editor-root --json` before each tracked write set.
- No production behavior change without a failing test first.
- Preserve source-budget baseline `2dab77f169eceb2d45f917358c2a7487e7ac8db6` and both unexpired debt records byte-for-byte.
- Do not extend an expired date, create umbrella debt, delete active leases/current proof, or remove recovery sources before verified archival.
- Stop after local publish readiness; do not remote push.

---

### Task 1: Tracked projection and scaffold retirement

**Files:**

- Delete: `.ethos/ENGINEERING-NOTES.md`
- Delete: `.ethos/terminal-landing-plan.md`
- Delete: `.ethos/assistants.toml`
- Delete: `packages/ethos/src/ethos/repository/adoption/scaffold/template_files/core/assistants.toml.j2`
- Modify: `.ethos/project.toml`
- Modify: `.ethos/release.toml`
- Modify: `packages/ethos/src/ethos/repository/adoption/scaffold/template_files/core/project.toml.j2`
- Modify: `packages/ethos/src/ethos/repository/adoption/scaffold/template_files/core/release.toml.j2`
- Modify: `packages/ethos/src/ethos/repository/adoption/scaffold/template_files/manifest.toml`
- Modify: `evidence/claims/stashless-residue-closeout.toml`
- Test: `tests/unit/adoption/test_scaffold_templates.py`
- Test: `tests/unit/adoption/test_apply_sample.py`
- Test: `tests/unit/release/test_policy_attestation.py`

**Interfaces:** Retain only `[command_plane].public = "ethos"` as the external-runner marker; assistant projections remain sourced by activation/system contracts.

- [ ] Write assertions that scaffold output omits `.ethos/assistants.toml`, product/scaffold project config contains the runner marker, and dead release keys are absent.
- [ ] Run the focused tests and confirm they fail against current templates/config.
- [ ] Apply the smallest product/template/manifest deletions and update the stale historical claim target.
- [ ] Re-run focused tests, config lint, and scaffold digest checks until green.
- [ ] Commit as one projection-parity change.

### Task 2: Lossless Rules V2 migration and command

**Files:**

- Modify: `packages/ethos/src/ethos/repository/policy/rules/migration.py`
- Modify: `packages/ethos/src/ethos/domain/plan.py`
- Modify: `packages/ethos/src/ethos/surface/cli/rules.py`
- Modify: `packages/ethos/src/ethos/repository/adoption/scaffold/template_files/core/rules.toml.j2`
- Modify: `.ethos/rules.toml`
- Test: `tests/unit/kernel/rules/test_migration.py`
- Test: `tests/unit/domain/test_plan.py`
- Create: `tests/unit/cli/test_rules_migration.py`
- Test: `tests/unit/adoption/test_apply_sample.py`

**Interfaces:** `migrate_legacy_rules(root, apply=False)` returns a lossless target; CLI apply requires `--authorize --expect-head`, prewrite admission, and compare-and-swap.

- [ ] Add tests proving `[quality]`, standards, determinism, formats, artifacts, gates, and unknown active tables survive while rule keys normalize.
- [ ] Add CLI red tests for dry-run, missing authorization, HEAD mismatch, protected root, and admitted Work Lane apply.
- [ ] Add plan red tests showing V2 `path_globs` and `required_gates` still select gates.
- [ ] Implement lossless text preservation, guarded CLI wiring, and normalized plan consumption.
- [ ] Migrate the product/scaffold rules shape and correct durable evidence roots without editing debt amounts yet.
- [ ] Run rules, planning, scaffold, format-policy, config-lint, and Python lint checks; commit.

### Task 3: SQLite v2 and conservative maintenance

**Files:**

- Modify: `packages/ethos/src/ethos/adapters/store/state/events.py`
- Modify: `packages/ethos/src/ethos/adapters/store/state/lease/projection.py`
- Modify: `packages/ethos/src/ethos/adapters/store/state/lease/lifecycle/effects.py`
- Modify: `packages/ethos/src/ethos/adapters/mutation/proof.py`
- Create: `packages/ethos/src/ethos/adapters/store/state/maintenance.py`
- Modify: `packages/ethos/src/ethos/surface/cli/root/inspection.py`
- Modify: `docs/architecture/local-state.md`
- Test: `tests/unit/lanes/test_state.py`
- Create: `tests/unit/lanes/test_local_state_maintenance.py`
- Create: `tests/unit/mutation/test_proof_retention.py`

**Interfaces:** `local_state_maintenance_inventory(root, archive_root, observed_at)` produces a digest; `apply_local_state_maintenance(..., expect_inventory_digest, confirm_irreversible)` applies only the exact re-observed plan.

- [ ] Add SQLite red tests for empty-table v2 migration, non-empty fail-close, rollback, and idempotence.
- [ ] Add lease red tests for expired orphan deletion and preservation of active/ref/worktree/path/malformed cases.
- [ ] Add proof red tests for current/ref/worktree/live-lease protection and unreachable deletion.
- [ ] Add archive red tests for absolute external root, complete copy, digest mismatch, extraction failure, bundle failure, and idempotence.
- [ ] Implement the minimal shared inventory/apply model and expose it as explicit `doctor` maintenance options; keep default doctor read-only.
- [ ] Run focused state/proof/CLI tests and lint; commit before touching real local state.

### Task 4: Recovery archive and ignored-state cleanup

**Files:**

- Modify: `evidence/chronicle/history-residue-closeout-20260719/2026-07-19.md`
- Modify: `evidence/claims/history-residue-closeout-20260719.toml`
- Local source: `<accepted-root>/.ethos/state/residue-snapshots/`
- Operator archive: `$HOME/.local/share/ethos/recovery/history-residue-closeout-20260719/`

**Interfaces:** The tracked Chronicle binds archive path, entry-manifest digest, archive digest/size, three bundle identities, verification commands, and starting/final HEAD without promoting raw local state.

- [ ] Dry-run maintenance against the accepted root and record the inventory digest and exact counts.
- [ ] Copy the full snapshot set, generate entry hashes, create the archive, extract-test it, and run `git bundle verify` on all three bundles.
- [ ] Update Chronicle and claim digest with the verified receipt.
- [ ] Apply maintenance using the dry-run digest; reject and re-plan if any local fact changed.
- [ ] Verify schema v2, retained active leases/current proof, pruned candidates, verified archive, and absent source snapshot directory.

### Task 5: Retire bundled provider executables and compress tests

**Files:**

- Delete: `extensions/independent-verification/adapters/independent_identity/reference_verifier.py`
- Delete: `extensions/independent-verification/adapters/generic_git/pre_receive.py`
- Delete or reduce: `extensions/independent-verification/tests/`
- Modify: `packages/ethos/src/ethos/adapters/admission/evidence/external.py`
- Delete: `packages/ethos/src/ethos/repository/evidence/attestation.py`
- Modify: `docs/governance/independent-verification-adoption.md`
- Modify: `docs/architecture/package-ontology.md`
- Modify: `docs/decisions/accepted/DR-0006-proof-trust-boundary.md`
- Modify: owner tests under `tests/unit/admission/` and `tests/unit/lanes/`

**Interfaces:** Provider-neutral receipt validation stays in product source; operator executable examples are no longer shipped.

- [ ] Move indispensable receipt assertions into canonical admission tests and verify they fail before consolidation.
- [ ] Consolidate semantic-attestation and external receipt parsing into one typed validator.
- [ ] Remove the two reference executables and stale product-shipping claims/docs while retaining external operator guidance.
- [ ] Run receipt/admission/claim/OpenSpec tests and confirm `python_other <= 446`.
- [ ] Commit the adapter-boundary change.

### Task 6: Settle Python product and test debt

**Files:**

- Refactor: `packages/ethos/src/ethos/adapters/openspec/lifecycle/`
- Refactor: `packages/ethos/src/ethos/adapters/mutation/lane_lifecycle/projection_rebase/`
- Refactor: `packages/ethos/src/ethos/adapters/admission/`
- Refactor: `packages/ethos/src/ethos/adapters/mutation/closeout/`
- Refactor: `packages/ethos/src/ethos/repository/policy/performance/`
- Reduce/remove: nine `tests/unit/coverage/*` historical edge suites listed in the design evidence.
- Preserve/move assertions into owner suites under `tests/unit/{admission,lanes,product,governance,domain}/`.

**Interfaces:** Public command payloads, gap codes, schema validation, and 100% coverage remain unchanged; only duplicate representation is deleted.

- [ ] Measure each candidate suite/module with the source-budget command and coverage report.
- [ ] For each semantic owner, write or retain the smallest failing owner test before deleting duplicate code/tests.
- [ ] Consolidate receipt stack by at least 600 product eLOC, OpenSpec lifecycle by 600, lane recovery/read models by 750, closeout/publication by 500, and temporary performance/declaration wiring by 437.
- [ ] Remove 4,662 net test eLOC while moving every unique assertion into owner tests and retaining 100% coverage.
- [ ] Run focused owner tests after each slice and the full suite after the final slice; commit only green slices.

### Task 7: Settle tools, shell, TOML, Jinja, and debt ledger

**Files:**

- Delete/merge: `tools/ci/structural_whitespace.py`
- Reduce: `tools/ci/ci_templates.py`
- Delete/merge: `tools/ci/ethos_core_build_hook.py`
- Delete/merge: `tools/ci/scripts/run-performance-evidence.sh`
- Delete/merge: `tools/ci/scripts/run-head-bound-proof.sh`
- Consolidate: `tools/ci/scripts/with-python-runtime.sh` call sites
- Modify: `.ethos/rules.toml`
- Modify: `system/commands.toml`
- Modify: scaffold Jinja templates and retired temporary claim carriers only after reachability checks.

**Interfaces:** Owner scripts remain the single command bodies; CI/hooks only project them; config and claim schemas stay valid.

- [ ] Write/retain owner tests for every shell/tool behavior before removing duplicate wrappers.
- [ ] Reach `python_tools <= 1038`, `shell <= 1552`, `toml <= 11846`, and `jinja <= 671` without excluding carriers from measurement.
- [ ] Run claim reachability and archive/history checks before deleting temporary active claim TOML.
- [ ] Remove the ten expired records and unused waves only after all category limits pass; retain the two unexpired records unchanged.
- [ ] Run source-budget and verify zero expired or exceeded gaps; commit.

### Task 8: Closeout evidence and lifecycle

**Files:**

- Modify: `openspec/changes/history-residue-closeout-20260719/tasks.md`
- Modify: `evidence/chronicle/history-residue-closeout-20260719/2026-07-19.md`
- Modify: `evidence/claims/history-residue-closeout-20260719.toml`
- Regenerate if stale: `evidence/parity/generic-shadow.json`

**Interfaces:** Final evidence distinguishes local executed proof, local publish readiness, and deferred hosted/remote state.

- [ ] Mark completed OpenSpec tasks and append final metrics, archive receipt, maintenance result, and verification commands.
- [ ] Recompute the Chronicle SHA-256 in the active claim and run claims/OpenSpec strict validation.
- [ ] Run all focused owner scripts, `tools/ci/scripts/run-python-tests.sh`, and source-budget.
- [ ] Commit parity-relevant changes, run parity gaps, regenerate/commit generic shadow if required.
- [ ] Run `status`, `plan --changed`, and HEAD-bound executed proof.
- [ ] Land to candidate and run local publish readiness; report remote push and hosted observations as deferred.
