# Proposal

## Why

The CI model that adopters render their workflows from pins `jdx/mise-action` v5.2.6
(`.config/ci/verification.cue:59`). v5.2.7, commit `b44d12e7d0d8ee7461bb893e1b1993500433185b`,
was published on 2026-11-06T17:03:39Z, is the newest release and has been public for more than 24
hours; its download failures now log the status and host, and its retries back off longer.
Adopters move only through an ETHOS release, so the model takes it here.

The proof of `catalog-root` (archived) also found two process tests whose console stub still
replaces the application's former `app` and `dispatch_arguments`; the console now runs
`run_application`, so the stub never ran its child. Their repair rides here, since an archived
Change admits no further paths.

## What Changes

- The shipped CI model pins `jdx/mise-action` at v5.2.7 by its full commit.
- The nested-group cancellation test stubs `run_application`, as the other console stubs do.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

## Impact

- `.config/ci/verification.cue`; adopters take the new pin when they regenerate their workflows
  from a release that carries it. ETHOS's own workflows do not run the action.
- `tests/unit/adapters/test_process.py`.
