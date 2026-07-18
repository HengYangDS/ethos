## Context

ETHOS presently has one host-profile reader, one implicit `origin` publication
target, and provider CI that includes the local-only candidate branch. The
result does not represent the requested equal GitLab/GitHub publication planes.
The predecessor lane contains a useful, unlanded implementation, but it is
foreign, dirty, and stale; this successor re-derives only the required behavior
on the current candidate base.

## Goals / Non-Goals

**Goals:**

- Model local verification/install, GitLab, and GitHub as three explicit
  layers, with GitLab and GitHub equal in repository, CI/CD, and publication
  capability.
- Make a named remote and branch role part of pre-push admission.
- Keep `candidate/dev` and every `work/*` branch local-only; allow only `dev`,
  `main`, and `submit/*` at declared remote targets.
- Let `publish` observe both targets independently without pushing or claiming
  hosted success.
- Keep generated provider workflows exact projections of their templates.

**Non-Goals:**

- Push, configure, or privilege either remote; remote observations do not
  establish publication.
- Change candidate or accepted closeout authority, relax proof, or alter the
  official OpenSpec schema.
- Mutate the predecessor lane, DDWG, or any other foreign worktree.

## Decisions

1. Parse `[publication]` from `.ethos/release.toml` in a small release reader.
   It validates exactly two named remote records and returns a legacy read-only
   projection only for adopters that have not yet declared the new contract.
2. Put remote-ref admission beside existing pre-push proof admission. The
   branch-role decision is evaluated before proof lookup, so a candidate or
   unknown target cannot become legal merely by carrying a proof receipt.
3. `publish` retains its no-push contract. It records per-target availability
   and tracking observations, then exposes a summary that distinguishes no
   target, one target, two available targets, and synchronization.
4. Provider triggers are a repository policy projection: both templates run
   only for `dev`, `main`, and `submit/*`; `candidate/dev` is deliberately
   absent from both. Scaffold templates produce the same topology.

## Risks / Trade-offs

- [An adopter declares only one remote] -> the reader emits a stable topology
  gap rather than silently treating GitLab as authoritative.
- [A hook receives an undeclared remote name] -> the hook blocks before the
  push moves any ref.
- [One remote is unavailable] -> the other remains an independent observation;
  no availability result is promoted to a remote push or hosted-CI claim.
- [The predecessor patch has stale helper shapes] -> RED tests are added on the
  current base and implementation remains minimal rather than cherry-picking
  the foreign history.

## Migration Plan

1. Add the declaration and reader with RED-to-GREEN tests.
2. Wire hook, publish, CI projections, and scaffold templates.
3. Regenerate parity evidence, execute HEAD-bound proof, and land locally.
4. Validate GitLab and GitHub separately after local closure; neither remote
   state is inferred from the other.

## Open Questions

None. Remote URLs and hosted execution remain external observations, not
configuration targets for this Change.
