---
subject: ethos:artifact-topology-detached-residue-absorption-20260724
role: plan
state: active
relations:
  source_lane: work/artifact-topology-hotpath-20260714
  change: openspec/changes/archive/2026-07-24-artifact-topology-detached-residue-absorption
---

# Artifact-Topology Detached Residue Absorption Design

Status: active local-only authority design.

Purpose: bind one exact ownerless dirty artifact-topology residue to the current
behavioral disposition and a later native preserve-retire transition.

See also: [Implementation Plan](artifact-topology-detached-residue-absorption-implementation-plan-20260724.md),
[Mutation Rules](../../rules/mutation.md), and
[Evidence Rules](../../rules/evidence.md).

Date: 2026-07-24.

## Context

The registered historical worktree for
`work/artifact-topology-hotpath-20260714` was left detached at
`70defe82f306708badf1cfabe0c3f8fa917287fa` with four unstaged tracked files.
Its branch ref was absent, no current session used the worktree as a checkout,
no process occupied the path, and the newest dirty file timestamp was
2026-07-14.  Before normalization, the exact binary patch SHA-256 was
`6a84df8a7b28d703f82f1bcac0ee61e8534874438e25c7376c38d8c81f5a404a`.

The historical branch name was reconstructed at the exact detached HEAD and
attached to the existing registered worktree without changing working bytes.
The normalized lane is now a linked, dirty, missing-lease, missing-Claim,
accepted-ancestor Work Lane.  This reconstruction is coordination repair, not
ownership, semantic acceptance, or retirement authority.

## Options considered

### 1. Current semantic judgment plus native preserve-retire — selected

Bind the exact source observation and patch digest to current accepted
artifact-topology semantics.  Preserve-retire only after focused proof, carrier
land, and accepted closeout.  Keep package clearing as a later manifest-bound
decision.

This preserves recoverability while avoiding historical implementation replay.

### 2. Replay the dirty implementation — rejected

The dirty bytes use identity-keyed weak-reference CEL caches and collapse a
denied directory to one path.  Current accepted source instead caches complete
immutable path decisions and retains exact denied leaf visibility while
bounding traversal.  Replaying the older implementation would restore more
state and weaker evidence granularity without a current product gap.

### 3. Reset or force-remove the worktree — rejected

The worktree contains unique dirty bytes.  Cleanliness of its committed HEAD
and lack of an active owner do not authorize discarding them.

## Semantic disposition

| Historical concern | Current accepted owner | Disposition |
| --- | --- | --- |
| Reuse immutable artifact-policy results | `03ff8bb33` and current `_cached_path_policy` | Absorbed through a safer whole-decision cache |
| Bound topology scan work | `7c877872a` and current prefix/prune filtering | Absorbed by the current bounded reader |
| Avoid repeated CEL policy projection | Current whole-decision cache and shared CEL contract owners | The useful performance goal is absorbed; the weakref/id cache is rejected |
| Collapse every denied subtree to one directory result | Current exact denied-path reporting | Rejected because it weakens evidence specificity |
| Preserve focused regression coverage | Current topology and CEL suites | Absorbed by current tests and proof gates |

## Lifecycle

1. Promote this target-specific design, Claim, Chronicle, and OpenSpec delta.
2. Validate focused current behavior and exact source observation.
3. Archive and prove the carrier at one immutable HEAD.
4. Land to candidate and perform accepted-root closeout as a separate step.
5. Record and apply one native `lane_resolution/preserve-retire` decision for
   the exact source lane.
6. Verify the package, receipt, branch absence, worktree absence, and accepted
   root cleanliness.
7. Author a separate manifest-bound clear decision only if the retained package
   contains no behavior absent from accepted truth.

## Failure policy

Any source-head, dirty-path, patch-digest, lease, Claim, worktree-registration,
accepted-head, Chronicle, process-occupancy, or package-integrity drift blocks
the effect.  No raw ref deletion, force removal, remote mutation, or unrelated
lane cleanup is authorized.

## Success criteria

- Current accepted tests prove the useful artifact-topology semantics.
- The old implementation is not replayed merely for byte retention.
- Native preserve-retire captures the exact dirty payload before removing only
  the named branch and worktree.
- A durable receipt remains, and package clearing stays separately authorized.
