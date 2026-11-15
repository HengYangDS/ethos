# Proposal

## Why

After an apply that wrote the release's pin, `ethos adopt` names `mise lock` as the next action.
The command names no directory, so it locks the configuration that the caller's working directory
selects. An agent that adopted a repository through `--root` from another directory runs it in the
wrong place. The requirement that owns this continuation already says that the caller's working
directory does not change the selection, and the product's three other Mise next actions name the
directory with `--cd`: the locked install, the trust and the bootstrap.

`adopt-pin` withdrew the question under DR-0016, because the bare form was the approved text. The
owner decided it on 2026-11-15: the next action carries the repository's path.

## What Changes

- After an apply that wrote the pin, the next action is `mise --cd <root> lock`, with the adopted
  root.
- The command-plane requirement, the adoption architecture page and the unreleased changelog entry
  say the same.

Not breaking: the bare form has shipped in no release. The step stays an instruction and is no
command of the product.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: the requirement `Adoption continuation preserves request meaning` names the
  rooted form.

## Impact

`src/ethos/application/adoption.py`, `tests/unit/adoption/test_pin.py`,
`openspec/specs/command-plane/spec.md`, `docs/architecture/adoption-profiles.md` and
`CHANGELOG.md`.
