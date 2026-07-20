## Why

The canonical Python policy still suppresses `EM102` through both the Ruff
ignore list and ignored-rule ratchet. Its two remaining findings are local
validation messages in `ProofRun`.

## What Changes

- Bind each dynamic validation message before raising it.
- Remove `EM102` from both canonical exception carriers.
- Shrink the exact `TRY003` ratchet from 10 to 8 because binding the two messages removes two existing `TRY003` findings; `TRY003` remains explicitly tracked debt.
- Prove direct rule enforcement through the existing owner gate and lifecycle.

## Capabilities

### Modified Capabilities

- `quality`: direct `EM102` enforcement; subject=quality:python-em102;
  reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=ci;
  facet:authority=source.

## Out Of Scope

- Remaining quality debt, foreign lanes, hosted CI, publication, and terminal
  exception-free quality.
