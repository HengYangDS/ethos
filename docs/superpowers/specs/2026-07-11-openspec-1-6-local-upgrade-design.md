# OpenSpec 1.6 Local Upgrade Design

## Objective

Converge the workstation and the canonical `ethos`, `alphasim-dmgr-fix-b3`,
and `di-effect` repositories on official OpenSpec `1.6.0`, including the new
`update` planning workflow, while preserving repository authority boundaries,
historical evidence, and foreign Work Lane ownership.

## Current State

- The official stable npm release is `@fission-ai/openspec@1.6.0`.
- `/Users/yheng/.local/bin/openspec` already resolves to `1.6.0` through the
  host-managed floating `npx --yes @fission-ai/openspec` launcher.
- `/Users/yheng/.config/openspec/config.json` preserves the pre-1.6 custom core
  workflow set and therefore omits `update`; delivery is `skills` only.
- `/Users/yheng/.codex` has no OPSX command prompts.
- The JetBrains Codex home contains stale pre-1.6 OPSX prompts and has no
  `opsx-update.md`.
- `alphasim-dmgr-fix-b3` pins OpenSpec `1.5.0`, while its tracked generated
  Codex and Claude skills report `generatedBy: "1.4.1"`.
- `di-effect` pins the agentic container and environment example to `1.4.1`.
- ETHOS active runtime/bootstrap surfaces use an unversioned OpenSpec package;
  historical claims and chronicles contain immutable observations of `1.5.0`.
- OpenSpec `1.6.0` currently validates all three canonical workspaces:
  ETHOS `9/9`, alphasim `22/22`, and di-effect `27/27`.

## Authority and Scope

### Authoritative mutation targets

1. Host OpenSpec configuration and the two active Codex homes:
   - `/Users/yheng/.config/openspec/config.json`
   - `/Users/yheng/.codex`
   - `/Users/yheng/Library/Caches/JetBrains/PyCharm2026.1/aia/codex`
1. Canonical repository branches through owned isolated Work Lanes:
   - `/Users/yheng/projects/ethos`
   - `/Users/yheng/projects/alphasim-dmgr-fix-b3`
   - `/Users/yheng/projects/di-effect`

### Explicit exclusions

- Do not mutate candidate checkouts, preservation trees, archived sessions, or
  existing task/worktree copies directly.
- Do not modify foreign or owner-unknown Work Lanes.
- Do not rewrite archived OpenSpec changes, historical evidence, chronicles,
  or dated version inventories merely because they record older versions.
- Do not overwrite the untracked alphasim `.agents/skills/openspec-*` residue
  in the protected primary checkout.
- Do not touch the unrelated uncommitted `di-effect` primary-checkout changes.

## Design Decisions

### 1. Version policy

- Repository-owned automation, containers, templates, and executable pins use
  the exact version `1.6.0` for reproducibility.
- The host launcher remains the existing host-managed floating update channel;
  the upgrade gate records and verifies that its effective version is `1.6.0`.
- A future OpenSpec release is a new dependency-upgrade event, not an implicit
  reason to rewrite repository pins.

### 2. Global workflow profile

- Replace the stale custom profile with the official `core` profile.
- Set delivery to `both` so Codex receives repository-local skills and global
  OPSX prompts where the tool supports both.
- The resulting core workflow set is:
  `propose`, `explore`, `apply`, `update`, `sync`, and `archive`.
- Preserve telemetry identity and unrelated feature flags.

### 3. Dual Codex projection

- Regenerate OPSX commands for both the standard Codex home and the
  JetBrains-managed Codex home by running the official updater with an explicit
  `CODEX_HOME` for each projection.
- Both homes must contain the six core command prompts, including
  `opsx-update.md`.
- Restarting or terminating Codex/PyCharm is outside this change. Filesystem
  readiness is verified now; user-visible reload remains a separate lifecycle
  action requiring explicit approval.

### 4. Repository-specific adaptation

#### ETHOS

- Pin active OpenSpec bootstrap, fallback, and adopter scaffold surfaces to
  `1.6.0` where the repository owns executable tool supply.
- Preserve the rule that OpenSpec is a governance carrier, not a second ETHOS
  command plane.
- Add or update focused contracts proving the selected official version and
  the 1.6-compatible failure semantics used by automation.
- Do not add tracked vendor-specific OpenSpec skills unless ETHOS already owns
  that projection surface.

#### alphasim-dmgr-fix-b3

- Update `pyproject.toml` and `justfile` pins from `1.5.0` to `1.6.0`.
- Regenerate existing tracked official Codex and Claude OpenSpec skills with
  OpenSpec `1.6.0`.
- Add the new `openspec-update-change` skill and register it in the existing
  agent-surface and readiness contracts.
- Keep repository-authored `.agents` skills separate from official-managed
  vendor projections; do not absorb protected-checkout residue into the lane.
- Refresh only current dependency/tooling documentation or new dated evidence;
  do not edit historical inventories.

#### di-effect

- Update the agentic OpenSpec container default and environment example from
  `1.4.1` to `1.6.0`.
- Update focused readiness/version tests and active guidance where they encode
  the current default.
- Preserve official CLI semantics as primary and do not introduce a new
  vendor-specific tracked root.

### 5. OpenSpec 1.6 behavior compatibility

Repository wrappers and tests must account for the release's observable
changes:

- blocked human-mode archives exit non-zero;
- stale `MODIFIED` requirements stop rather than deleting newer scenarios;
- nested specs and task files resolve consistently across list, view,
  validation, progress, and archive checks;
- fenced examples, metadata, multiline descriptions, nested deltas, and
  normative keywords receive stricter and more consistent parsing;
- `/opsx:update` changes planning artifacts only and requires confirmation
  before each artifact write.

The upgrade does not weaken repository-specific gates to accommodate 1.6.
Where behavior differs, adapters and tests converge on official semantics.

## Execution Order

1. Capture pre-change versions, hashes, Git state, and validation summaries.
1. Update the global OpenSpec profile and dual Codex projections.
1. Implement and verify the ETHOS repository pin/adaptation lane.
1. Implement and verify the alphasim pin, generated-skill, and contract lane.
1. Implement and verify the di-effect container/runtime lane.
1. Re-run host, repository, and cross-surface drift checks.
1. Close each lane through its repository-native lifecycle; keep remote
   publication separate from local acceptance.

## Verification Matrix

### Host

- `openspec --version` returns `1.6.0`.
- `npm view @fission-ai/openspec version` returns `1.6.0` at audit time.
- `openspec config list` reports `profile: core`, `delivery: both`, and the six
  core workflows.
- Both Codex homes contain the six current OPSX prompts.
- Generated OpenSpec skills report `generatedBy: "1.6.0"`.

### ETHOS

- Focused tool-supply and OpenSpec adapter tests pass.
- `openspec validate --all --strict --json` passes.
- ETHOS OpenSpec lifecycle and repository proof gates pass for the changed
  scope.

### alphasim-dmgr-fix-b3

- Pin-parity and agent-surface tests pass.
- `pixi run openspec-check` passes with the `1.6.0` pin.
- Skill activation/projection checks recognize `openspec-update-change`.
- Changed-scope quality and proof gates pass.

### di-effect

- Agentic toolchain/version tests pass.
- Container configuration resolves `DI_EFFECT_AGENTIC_OPENSPEC_VERSION=1.6.0`.
- Official OpenSpec validation and repository changed-scope gates pass.

## Rollback

- Host rollback restores the captured OpenSpec config and prompt directories.
- Repository rollback reverts only the lane commits; historical files and
  unrelated user work remain untouched.
- A repository may remain on its previous pin temporarily if its 1.6 lane
  fails its own gates, but the failure must be reported explicitly rather than
  hidden behind a floating dependency.

## Acceptance Criteria

The upgrade is complete only when:

1. the effective host CLI is `1.6.0`;
1. both Codex homes expose the 1.6 core workflows including `update`;
1. all current repository-owned OpenSpec pins are `1.6.0`;
1. all three canonical repositories pass official OpenSpec validation and
   their relevant local gates;
1. no foreign lane, protected checkout, historical record, or unrelated dirty
   file was mutated; and
1. local acceptance and remote publication state are reported separately.
