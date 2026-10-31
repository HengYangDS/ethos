# Proposal

## Why

On 2026-10-31 the owner directed that re-exports, shims, wrappers, aliases and renames that add no
independent semantics be removed and that their return be prevented by mechanism. The read-only
inventory of `22657d501` (`build/runtime/work/pass-through-removal/inventory.md`) found the facade
forms already at zero: no import-only module, no `__all__`, and the module-layout gate clean. What
remains is smaller and still real:

- eight product pass-throughs and two product assignment aliases, 45 effective lines that only
  forward to another owner;
- fourteen renaming `from m import y as z` aliases in product and tools code, and seven imports that
  reach a name through a module that does not define it;
- no check for either alias form, although `rules/module-layout.md` 2.5 and 2.5.1 forbid both and
  the quality specification's "Semantic And Physical Isomorphism" requirement makes aliases and
  imports that do not resolve to the defining owner block proof.

## What Changes

- Remove the measured product pass-throughs: fold `command_data_validation` into
  `workspace_status_validation`; construct `DocstringStyleIssue` directly; replace
  `proof_artifact_root` with `local_state_root`; construct `RepositoryProfileDeclaration` instead of
  calling `bootstrap`; inline `_validated_member` and `_repo_root`; fold `_working_content_sha256`
  into `dirty_content_sha256`; inline `archive_projection_updates`; use
  `HISTORICAL_SURFACE_PREFIXES` and `REQUIRED_RELEASE_FILES` under their own names.
- Remove the renaming aliases. Where an alias names the concept better than its owner, the owner
  takes that name (`validate_git_effect_attestation`, `compile_gate_declaration`,
  `compile_gate_policy`, `compile_governed_branch_intent_report`, `compile_openspec_shape_report`);
  otherwise the importer uses the owner's name.
- Import each name from the module that defines it.
- The module-layout gate refuses a renaming from-import alias unless another binding in the module
  holds the original name, and an import of a name through a governed module that does not define
  it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The quality specification already requires the behavior; this Change implements its checks.

## Impact

- Product code: about minus 45 lines of pass-throughs plus about 20 lines of checks; tools: minus 1.
- Tests: patches and imports that named a removed function move to its owner; new red and green
  cases for both checks.
- Out of scope: `emulator_evidence_command` and the four module aliases in
  `tools/ci/ci_templates.py` retire with the CI provider emulation in their own Change; the
  `openspec_base_command` test seam and the constant-binding wrappers stay, as the inventory
  recommends.
