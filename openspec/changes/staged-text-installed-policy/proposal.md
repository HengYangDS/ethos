# Proposal

## Why

Since batch 3 landed (dev 21fbc6034), the hook runtime built from it refuses every commit in the
ETHOS repository with
`format_selection_increment_invalid:.config/checks/format-selection/policy.toml`. The staged text
check asks `format_ownership`, which reads the repository's own policy file as a byte-bound carrier
increment whenever that file is not the runtime's shipped policy file
(`src/ethos/adapters/gates/native/inputs.py:169-175`). In a source checkout it is the same file;
under an installed runtime the shipped policy is a copy at another path, so ETHOS's full policy,
with its `source_budget` table and every ownership row, fails the increment rules. Proofs run from
source and never reach this path.

## What Changes

- The staged text check reads the canonical-text rows from the shipped policy
  (`canonical_text_paths` with `canonical_resource`), and it excludes received and carrier paths
  through `paradigm_received_paths`, which already reads an invalid increment as none. It no longer
  asks `format_ownership`.
- A regression test runs `pre-commit` in a repository that keeps the full policy file while the
  runtime's shipped policy lives at another path.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The staged rules are unchanged; only their policy source is, so `skip_specs: true` applies.

## Impact

`src/ethos/adapters/repo/hook/staged_text.py`, `tests/unit/adapters/repo/hook/test_staged_text.py`
and a CHANGELOG Fixed line.
