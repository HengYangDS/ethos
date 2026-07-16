# all-work-lanes-convergence-20260716

## Why

The repository currently retains 60 legacy `work/*` refs whose graph,
worktree, lease, and semantic states differ. Some are accepted ancestors, some
were superseded, some contain still-valid implementation intent, and some have
dirty or owner-uncertain overlays. Ref names, stale records, and graph ancestry
alone cannot safely decide integration or deletion. A bounded governance
carrier is required to freeze the exact cohort, complete the remaining product
intent, preserve recoverability, and close the local lifecycle without turning
the user's current instruction into future wildcard authority.

## What Changes

- Add a tracked, digest-bound inventory of the exact legacy cohort plus the
  current governance carrier, including HEAD, worktree, dirty, lease, claim,
  graph classification, semantic family, and planned disposition facts.
- Establish a cohort-bound convergence program that re-observes every mutable
  target before effect, respects valid foreign holders, and requires accepted
  Chronicle evidence for exceptional missing-lease or irreversible resolution.
- Reconcile and implement the 11 semantic families carried by the legacy refs,
  using test-first current-candidate implementations instead of wholesale stale
  branch merges.
- Preserve dirty/owner-uncertain content before retirement, integrate or prove
  supersession, complete HEAD-bound proof, advance candidate and accepted roots
  through sanctioned ETHOS commands, and retire the exact cohort locally.
- Keep recovery-package clearing, remote Git push, and distribution publication
  outside this change.

## Capabilities

- `repository-governance`: subject=all-work-lanes-convergence-20260716;
  reuse=extend; change=modify; facet:lifecycle=work-lane-resolution,
  candidate-land,accepted-closeout,retirement; facet:surface=docs,openspec,
  evidence,test,source; facet:authority=user-instruction,git,lease,claim,
  accepted-chronicle,executed-proof

## Out of Scope

- No reusable authority over a `work/*` ref created after the frozen cohort.
- No impersonation of a valid lease holder or claim that process absence equals
  handoff.
- No Git stash, force push, raw protected-ref move, or unpreserved dirty-lane
  deletion.
- No clearing of existing lane-resolution recovery packages or receipts.
- No remote Git push, hosted-CI success claim, registry publication, or release
  distribution.
