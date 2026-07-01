---
subject: ethos:plan:closeout-and-evidence-seal
role: execution-plan
state: active
relations:
  governs: ethos-closeout-and-evidence-seal
---

# ETHOS Closeout And Evidence Seal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

Status: active.

Purpose: close the remaining ETHOS mechanism gaps around local accepted-root fast-forward, parity evidence refresh, command-plane next actions, configured branch-role semantics, substantive binding metadata, governed-repository unification, and shell command example scanning.

See also: [Command Plane](../../reference/command-plane.md), [Runner And Mutation](../../architecture/runner-and-mutation.md), and [Product Design Contract](../../governance/product-design-contract.md).

**Goal:** Replace hand-run closeout and evidence refresh steps with ETHOS-governed commands while preserving Git as product substrate and OpenSpec as mandatory governance dependency.

**Architecture:** Keep mutation mechanics in `ethos_adapters`, command orchestration in `packages/ethos`, repository reports in `ethos_repository`, and tests at the command and contract boundaries. Do not add a second command plane or provider-specific product semantics.

**Tech Stack:** Python 3.12, Cyclopts CLI, pytest, Ruff, JSON Schema, OpenSpec CLI, Git worktrees through ETHOS Work Lane commands.

---

## File Structure

- `packages/ethos-adapters/src/ethos_adapters/mutation.py`: add accepted-root fast-forward evaluation and apply logic.
- `packages/ethos/src/ethos/cli.py`: expose local closeout and parity evidence write options, fix next actions, and keep output JSON stable.
- `packages/ethos-repository/src/ethos_repository/parity.py`: add deterministic tracked parity evidence builders and file write helpers.
- `packages/ethos-repository/src/ethos_repository/command_registry.py`: classify local closeout and evidence-refresh commands without broadening the public workflow plane.
- `packages/ethos-repository/src/ethos_repository/coupling.py`: add substantive binding metadata and closeout/evidence commands to mechanism contracts.
- `packages/ethos-repository/src/ethos_repository/docs_registry.py`: normalize shell continuation lines before command-example classification.
- `tests/unit/test_workspace_apply.py`: mutation adapter tests for accepted-root fast-forward.
- `tests/unit/test_cli_contracts.py`: CLI tests for local closeout, next actions, configured roles, and command JSON.
- `tests/unit/test_parity_command.py`: parity evidence write and freshness tests.
- `tests/unit/test_command_registry_depth.py`: command-plane boundary tests.
- `tests/unit/test_coupling_governance.py`: binding taxonomy metadata tests.
- `tests/unit/test_docs_registry.py`: multiline shell command scanner tests.
- `tests/unit/test_workspace_lanes.py`: configured branch-role lifecycle coverage.
- `tests/architecture/test_product_boundaries.py`: governed-repository no-self surface regression.
- `docs/evidence/parity/alphasim-dmgr-shadow.json` and `docs/evidence/parity/generic-shadow.json`: final freshness refresh after implementation commits.

## Task 1: RED Tests For Local Closeout

- [x] Add adapter tests proving an accepted-root checkout can fast-forward only from the configured candidate branch when authorized, clean, and HEAD-matched.
- [x] Add CLI tests proving `ethos land --closeout --apply --authorize --expect-head <HEAD>` performs local accepted-root fast-forward and rejects dirty accepted root, stale expected HEAD, dirty candidate, and non-accepted-root invocation.
- [x] Verify RED with `uv run --group dev pytest tests/unit/test_workspace_apply.py::test_accepted_root_closeout_fast_forwards_configured_candidate_branch tests/unit/test_cli_contracts.py::test_land_closeout_apply_fast_forwards_accepted_root_from_candidate -q`.

## Task 2: GREEN Local Closeout

- [x] Implement `apply_candidate_to_accepted` in `ethos_adapters.mutation`.
- [x] Extend `ethos land` with `--closeout` while keeping existing Work Lane-to-candidate behavior unchanged.
- [x] Ensure all branch names come from `BranchRolePolicy`, including summary text and mutation records.
- [x] Verify GREEN with the RED command and `uv run --group dev pytest tests/unit/test_workspace_apply.py tests/unit/test_cli_contracts.py -q`.

## Task 3: RED Tests For Parity Evidence Write

- [x] Add tests proving `ethos parity shadow --write-evidence --adopter alphasim-dmgr --target <repo> --execute` writes tracked evidence with product HEAD, target HEAD, command digest, matched shadow summary, capabilities, dimensions, and basis.
- [x] Add tests proving `ethos parity gaps` next action points to the write-evidence command when evidence is stale.
- [x] Add tests proving generic evidence can be refreshed without an adopter special case.
- [x] Verify RED with `uv run --group dev pytest tests/unit/test_parity_command.py::test_parity_shadow_write_evidence_records_freshness_and_capability_basis tests/unit/test_parity_command.py::test_parity_gaps_recommends_write_evidence_when_tracked_evidence_is_stale -q`.

## Task 4: GREEN Parity Evidence Write

- [x] Add deterministic evidence builders in `ethos_repository.parity`.
- [x] Add CLI options `--adopter`, `--write-evidence`, and `--root` to `ethos parity shadow`.
- [x] Keep evidence freshness strict; do not accept arbitrary stale product heads.
- [x] Verify GREEN with parity tests and `uv run --package ethos ethos parity gaps --json`.

## Task 5: RED/GREEN Command Plane And Binding Metadata

- [x] Add tests proving `prove` next action for gapped audit is `ethos audit --mode deep`, not `ethos repository audit`.
- [x] Add tests proving local closeout and parity evidence refresh are classified as maintainer/reference or lifecycle commands, not new public workflow roots.
- [x] Add tests proving each binding registry entry includes `required_for`, `replaceability`, `degradation_state`, and `proof_gate`.
- [x] Implement minimal registry and coupling metadata updates.

## Task 6: RED/GREEN Configured Branch Roles And Governed Repository Unification

- [x] Add tests covering `land --closeout`, `publish`, submit branch planning, candidate status, and lifecycle summaries under a non-default branch policy.
- [x] Add product-boundary tests proving current product surfaces do not use retired `self` terminology and describe a governed repository subject instead.
- [x] Update code only where hard-coded default branch names still leak into runtime semantics.

## Task 7: RED/GREEN Shell Command Example Scanner

- [x] Add a docs-registry test with a multiline `uv run --package ethos ethos lane prewrite ... \` command.
- [x] Implement shell continuation normalization so continuation path lines are not reported as unknown command roots.
- [x] Verify with `uv run --package ethos ethos quality command-examples --json`.

## Task 8: Full Verification And Closeout

- [x] Run focused tests for every changed area.
- [x] Run `uv run --group dev pytest tests/unit tests/architecture -q`.
- [x] Run `uv run --group dev ruff check .`.
- [x] Run `uv run openspec validate --all --strict --json`.
- [x] Run `uv run --package ethos ethos playbooks check --mode v2-strict --json`.
- [x] Run `uv run --package ethos ethos report --json`.
- [x] Run `uv run --package ethos ethos prove --full --execute --expect-head "$(git rev-parse HEAD)" --json`.
- [x] Commit code changes, refresh parity evidence as a separate commit if HEAD freshness requires it, land to candidate, fast-forward accepted root through ETHOS local closeout, and retire only `work/ethos-closeout-and-evidence-seal`.

## Self-Review

- Spec coverage: local closeout, evidence refresh, next action, role configuration, binding metadata, governed repository unification, scanner continuation, proof, land, local closeout, and lane retirement are covered.
- Placeholder scan: no placeholder task remains; each task names exact files and verification commands.
- Type consistency: command names match current ETHOS CLI groups and adapter module boundaries.
