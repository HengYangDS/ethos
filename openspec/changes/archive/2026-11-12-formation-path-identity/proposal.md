# Proposal

## Why

A newcomer's first run on 2026-11-12 formed a repository under `/tmp` on macOS, where `/tmp` links
to `/private/tmp`. The `adopt --create` preview reported the canonical root and offered a
continuation that names it, and running that continuation verbatim refused with
`formation_plan_digest_mismatch`. The plan digest binds `requested_root`, the path as the caller
spelled it, so the canonical spelling of the same destination produced another digest. The
destination's identity is already bound twice: by the canonical root and by the parent directory's
device and inode, which apply checks again before it writes.

## What Changes

- The formation plan digest no longer binds the caller's spelling of the root. A preview and an
  apply that name one destination through different paths bind one plan; a parent retargeted
  between them still refuses.
- The Unreleased section of `CHANGELOG.md` gains a Fixed line.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: `Formation is an explicit adoption request` gains a scenario for a preview and an
  apply that spell one destination differently.

## Impact

`src/ethos/adapters/repo/starter/formation.py`, `tests/unit/adoption/test_greenfield.py` and
`CHANGELOG.md`.
