# Design

## Context

`per-file-ceiling-parameters` splits six ETHOS product modules to meet the 500-line default. The
new modules repeat imports and module docstrings, so the lane head measures `python_product` at
70,090 lines against a terminal budget of 70,000. `adapters/repo/git.py` still measures 509.

A read-only scan listed every public definition under `src/ethos` whose name, as a whole word,
occurs in no tracked file except its own definition and tests. A whole-word text search counts a
name inside a string, such as a provider reference in TOML or a `getattr` argument, as a use. The
scan skipped decorated framework hooks and names exported through `__all__`. It returned 23
candidates. Each was then read against its callers, its tests and the specifications that name its
behavior.

## Goals / Non-Goals

**Goals:**

- Remove product code that no consumer runs, so the splits fit the budget.
- Keep every behavior a live consumer depends on tested through that consumer's owner.
- Keep code that a specification still requires, and record the gap.

**Non-Goals:**

- Wiring or amending the two specifications whose behavior no live path runs.
- Simplifying the private parameters of functions that stay.

## Decisions

### 1. Disposition of the 23 candidates

Removed, because nothing but their own tests calls them:

| Function | Module | Also removed |
| --- | --- | --- |
| `exact_rename_target` | `adapters/repo/git.py` | |
| `set_local_config` | `adapters/repo/config_effects.py` | `_set_values`, `_values` |
| `compensate_created_paths` | `adapters/repo/git_effects.py` | |
| `stage_git_paths` | `adapters/repo/git_effects.py` | |
| `evaluate_cel_rules` | `contracts/policy/cel.py` | `CelRule` |
| `evaluate_cel_gap_groups` | `contracts/policy/cel.py` | `CelGapGroup` |
| `working_overlay_sha256` | `adapters/repo/dirty/change_provenance.py` | |
| `invoking_source_commit` | `adapters/repo/runtime/authority.py` | |
| `active_change_scope` | `repository/openspec/identifiers.py` | |

Without `evaluate_cel_rules` and `evaluate_cel_gap_groups`, `evaluate_cel_value` in the same module
has no product caller either. It goes with them, and its error case moves to
`evaluate_cel_predicate`, which the generated-artifact topology uses.

Removed, because a live function already owns the behavior:

| Function | Module | Live owner |
| --- | --- | --- |
| `repaired_ref_provenance` | `adapters/repo/commit/signature.py` | `repaired_peer_ref_provenance` |
| `publication_source_version_gaps` | `repository/release/publication.py` | `release_tag_policy` |
| `NodeSupply.verify_archive` | `adapters/repo/runtime/materialization/node/supply.py` | `NodeSupply.project` |
| `validate_ethos_result` | `repository/policy/schema.py` | `validate_schema_instance` |
| `load_system_contract` | `contracts/system/contracts.py` | `system_contracts_report` |
| `NativeSupply.executable_bytes` | `adapters/repo/runtime/materialization/native_supply.py` | `NativeSupply.payload_bytes` |
| `active_leases` | `adapters/store/state/lease/projection.py` | `lease_observations` |

Folded: `remove_untracked_tree` in `adapters/repo/git_effects.py` was a one-line wrapper around
`_remove_tree`, the containment check that `compensate_git_worktree` uses. The helper takes the
public name, so its tests stay as they are.

Kept:

- `release_policy_report` and `materialize_explicit_release`, see decision 3.
- `terminal_schema_documents`: the schema test compares its output with the committed
  `system/schemas/kernel/*.schema.json` files.
- `_BoundCalls.on_call_tool`, `pytest_addoption` and `pytest_sessionstart`: framework hooks that
  their frameworks call by name.

### 2. Tests follow the live owner

A test that exercises only a removed function is deleted. A case that only a removed function
covered moves to the live owner, for example the descendant check of `repaired_ref_provenance`
moves to `repaired_peer_ref_provenance`. A case that the live owner's tests already cover is
dropped: `release_tag_policy` already accepts a prerelease with build metadata, and
`committed_release_version` already rejects a malformed version source.

### 3. Specifications without a live path

Two kept functions implement requirements that no command runs:

- `repository-governance`, requirement "Release Policy", expects `ethos publish --json` to report
  release-policy gaps. `release_policy_report` in `repository/release/configuration.py` computes
  them, but `ethos publish` never calls it.
- `distribution`, requirement "Accepted release identity is immutable", describes an explicit
  release transition that admits before its effect and attests after it.
  `materialize_explicit_release` in `adapters/repo/runtime/transition.py` implements it, but no
  release path calls it.

Removing them would delete the only implementation of a stated requirement. Wiring them changes
release behavior and needs its own proof. After this lane lands, the lane owner proposes one
Change that wires each function into its command or amends the requirement, with evidence of what
currently protects an accepted release version. Review date: 2026-11-02.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| A name is called dynamically in a form the scan missed | The search covers every tracked file as whole words, including TOML and strings; the full proof runs every test. |
| A deleted test covered a case the live owner lacks | Decision 2 moves such a case to the live owner instead of deleting it. |
| A kept function keeps an unreachable path alive | Decision 3 names the next action and its review date. |
