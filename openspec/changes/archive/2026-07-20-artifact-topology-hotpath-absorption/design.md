## Context

The source changes generated-artifact scanning and CEL policy hot paths, plus a
standalone hygiene runner. Accepted source subsequently introduced newer
declaration, policy, cache, and runner arrangements. Historical bytes differ
because the source contains obsolete implementation and dated parity evidence.

## Decision

Use a current-base evidence carrier rather than replaying historical commits.
The carrier proves that current focused behavior enforces the source's useful
invariants, then permits only native `preserve-retire` for the source's dirty
state. The retained package is kept until a later independent clear decision.

## Risk Controls

- A changed source head, path, dirtiness, or lease observation blocks the
  native resolver.
- Current topology and CEL behavior must pass focused regressions before any
  lifecycle effect.
- Package preservation is verified before branch/worktree removal and does not
  prove absorption.
- The next destructive effect is one branch/worktree only; all other lanes and
  remotes remain out of scope.
