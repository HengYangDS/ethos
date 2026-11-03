# Design

## Context

See [proposal.md](proposal.md). `_from_import_aliases` in
`src/ethos/repository/policy/layout/facades.py` reports a public `from` import under another name
unless the imported object is a module or the importing module binds that name itself.

## Goals / Non-Goals

**Goals:**

- The `module-layout` gate passes on the lane head with the distribution acceptance's behavior
  unchanged.

**Non-Goals:**

- Renaming `mise_tool.run`, which reads as intended at its module-qualified call sites.

## Decisions

- **Import the module namespace.** `from tools.ci.delivery import mise_tool` is the form the policy
  admits and the one the tests already use, and the single call site reads `mise_tool.run`.

## Risks / Trade-offs

- [The new module was committed without a local module-layout run] → The lane's pre-commit checks
  for new modules now include the `module-layout` gate.
