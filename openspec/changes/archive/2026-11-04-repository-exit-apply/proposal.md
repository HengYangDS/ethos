# Proposal

## Why

`repository-exit` records, at install, the configuration that ETHOS replaces, and previews an
exit, but nothing applies one: a repository still leaves ETHOS only by hand, as two archived films
did on 2026-11-04. The preview also misses two review conditions, because a running process that
uses the runtime does not block it and it does not list unlanded branches. A repository that ETHOS
never adopted, or that was unbound by hand, previews as unrecorded and asks for a decision that has
no subject.

## What Changes

- `ethos adopt --exit --apply --authorize --expect-head <head> --expect-plan-digest <digest>`
  applies the exit under the runtime selection lock, in the reviewed order that
  [design.md](design.md) fixes. It writes a receipt before the first effect, restores the recorded
  configuration, verifies that no worktree still uses ETHOS's hooks, and only then removes the
  selectors and the record. A failure restores the prior state exactly.
- Inside the same fence, local generations are reclaimed through the proofs that
  `retire_generations` already makes, and each one it keeps is named as residue.
- Without a record, the exit refuses only while a hooks path that ETHOS owns remains, because only
  then would it have to guess. The user decides by setting or unsetting `core.hooksPath`; without
  such a path, the exit removes only the selectors.
- A repository with no selector and no hooks path that ETHOS owns is not adopted, and both the
  preview and the apply report `adoption_exit_not_adopted`. Hand-made files, such as
  `.git/ethos/unbound-*`, are never read as records.
- The preview refuses while a running process refers to the runtime or hooks generations, and it
  lists the topic branches that the accepted branch does not contain.
- Status reports an exit as a fact from its receipt.
- The MCP description, the CLI help and the command reference describe the apply.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `runtime-activation`: the exit preview's blockers and branch list, the exit's apply, and status
  after an exit.

## Impact

- `src/ethos/adapters/repo/hook/exit.py` and `observation.py`, and
  `src/ethos/adapters/repo/runtime/retirement.py`.
- `src/ethos/domain/adoption.py` and `src/ethos/surface/cli/root/adoption.py`.
- The command reference and the hook tests.
