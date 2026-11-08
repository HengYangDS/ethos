# Proposal

## Why

Native prewrite checks a patch against working files, so a valid index-only
patch cannot preserve unrelated unstaged content. Adopters need one native
admission boundary for selective staging rather than another staging controller.

## What Changes

- Add an explicit index target to the existing prewrite command; keep worktree
  admission as the default.
- Evaluate the exact patch through a disposable index and the existing staged
  admission, binding both real prestate and prospective tree.
- Refuse stale or unverifiable inputs without changing real staging, working
  files, refs or Lease state.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `adapters`: extend Prewrite Admission to exact index patches.

## Impact

The admission owner, lane CLI, focused admission tests and command reference
change. No new dependency, effect executor, permission token or compatibility
layer is introduced. Runtime selection, adopter mutation, broader governance
redesign and historical evidence migration are outside this Change.
