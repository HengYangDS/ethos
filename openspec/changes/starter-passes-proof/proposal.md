# Proposal

## Why

A newcomer's first run on 2026-11-12 formed a repository with `ethos adopt --create` and the
`foundation` starter. `status` reported it ready, but the first `prove` refused with 8
repository-paradigm gaps: no `CONTRIBUTING.md`, no shared rules in `.gitattributes` and
`.editorconfig`, no common rules for the four OpenSpec artifacts, and no toolchain owner. Six of
them have deterministic repairs in `lane repair-paradigm`; the other two exist only as gap text.
A starter that ETHOS writes should pass ETHOS's own paradigm on the commit that formation creates.

## What Changes

- Formation authors `CONTRIBUTING.md` and a task-only `.config/mise/config.toml` with the three
  verbs, then applies the paradigm's own repairs to the candidate, before the starter's inventory.
- Formation checks the composed candidate against the paradigm, with Git's view of its line
  endings, and refuses `formation_starter_paradigm_gap` before any effect when a gap remains. The
  `python-library` starter reports its remaining gaps instead, until its own conformance lands.
- The formation tests require an empty paradigm report on the formed commit.
- The Unreleased section of `CHANGELOG.md` gains a Fixed line.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: ADDED `Formation passes its own repository paradigm`.

## Impact

`src/ethos/adapters/repo/starter/formation.py`, `tests/unit/adoption/test_greenfield.py`,
`tests/unit/adoption/test_python_starter.py` and `CHANGELOG.md`. It depends on
`toolchain-lock-scope`, which lets a task-only mise configuration conform without a lock.
