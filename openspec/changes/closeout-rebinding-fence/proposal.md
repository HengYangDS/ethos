# Proposal

## Why

Accepted closeout renames legacy role refs and then rebinds each worktree on a renamed ref to its
successor. When the process stops between the two, worktrees name deleted refs, and every later
`land --closeout`, preview or apply, rewrites their `HEAD`s before any authorization or expected
head check: the preview writes with no authority, a refused apply writes too, and each rewrite is
an unconditional `git symbolic-ref` that overwrites a checkout made in between. The operation
catalog (`catalog-root`, review 1) needs every preview to read only, so this fence lands first.

## What Changes

- The closeout preview and `status` only read: they name each worktree left on a renamed legacy
  role ref with `branch_role_rebinding_pending:<ref>` and continue to the closeout apply bound to
  the head the root has after the binding.
- Only an authorized closeout apply with that expected head rebinds, each worktree by one
  compare-and-swap transaction of its `HEAD`; a refused apply binds nothing, and a worktree that
  moved after detection keeps its `HEAD` and blocks with `branch_role_worktree_binding_stale`.
- The rename, the retained-topic rename and the rebinding share that binder and first check that
  Git supports symbolic-ref transactions (Git 2.46 or later); without it they refuse with
  `branch_role_rename_git_unsupported` and move nothing.
- The rename preview no longer needs `--authorize`, and `next` for `ethos land --closeout --json`
  no longer reports a local write.
- The record retirement preview's refusal and foreign-record branches gain tests, and its artifact
  classification reads each file once: the full proof of `record-retirement-preview` found the
  suite's branch coverage at 94.97 % of the 95 % floor (11-08), every test passing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: accepted closeout's legacy role rename binds worktrees only in an
  authorized apply, by compare-and-swap, and needs Git 2.46 or later.

## Impact

- `src/ethos/adapters/mutation/branch_roles.py`, `src/ethos/application/land/operation.py`,
  `src/ethos/application/land/closeout.py` and `src/ethos/contracts/admission.py`.
- `tests/unit/lanes/test_legacy_role_rename.py`.
- `src/ethos/adapters/store/retention/kinds.py` and the retention and manifest tests under
  `tests/unit/adapters/store/retention/` and `tests/unit/lanes/retirement/`.
