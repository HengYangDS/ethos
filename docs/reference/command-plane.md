---
subject: ethos:command-plane
role: reference
state: active
relations:
  projects: ../governance/product-design-contract.md#semantic-kernel
---

# Command Plane

Status: active projection.

Purpose: define the complete public ETHOS command plane and its ownership
boundaries.

Canonical owner: [Product Design Contract](../governance/product-design-contract.md#semantic-kernel).

See also: [Quickstart](../guides/quickstart.md),
[Product Design Contract](../governance/product-design-contract.md#semantic-kernel), and
[OpenSpec Governance](../governance/openspec-governance.md).

## Public Roots

ETHOS exposes exactly these public roots:

| Root | Purpose | Read or effect boundary |
| --- | --- | --- |
| `ethos status --json` | Inspect repository facts, authority, gaps, coordination, and the next action. | Read-only projection; does not mint truth. |
| `ethos plan --changed --json` | Compile the changed-scope TransitionPlan and required gates. | Read-only. |
| `ethos prove --json` | Check proof readiness. | Read-only unless `--execute` is explicit. |
| `ethos land --json` | Report landing readiness. | Effects require the command's explicit guarded options. |
| `ethos publish --json` | Report local publication readiness. | Read-only. |
| `ethos publish --ref <full-ref> --probe-remote --expect-head <head> --json` | Derive an immutable exact-CAS request for one positively admitted branch or annotated release-tag ref from the exact local object and live declared peers. | Read-only; persists only content-addressed request evidence in Git private state. |
| `ethos publish --ref <full-ref> --probe-remote --apply --authorize --expect-head <head> --json` | Derive and consume the same full-ref publication request. | Uses the same receipt-bound exact-CAS executor as explicit receipt apply. |
| `ethos publish --receipt <path> --receipt-sha256 <digest> --apply --authorize --expect-head <head> --json` | Apply a previously derived full-ref publication request to its declared peers. | Rechecks the local object, trust binding, and all peers before the first push; returns attested peer-local partial effects if a later peer fails. |
| `ethos adopt --root <repo> --json` | Plan adoption for one repository. | Applying requires explicit authorization and an expected head. |

The public root anchors are `status`, `plan`, `prove`, `land`, `publish`, and
`adopt`. No reader, report, provider, or historical projection adds another
public root.

`status.data.hook_runtime` is the single hook-runtime
inspection surface. It reports installed and expected source commit/tree,
currentness, stable gaps, and the complete `ethos hook install` repair command;
status does not derive a parallel runtime verdict.

`ethos hook install --root <linked-worktree> --json` is one repository-family
repair operation. It activates one immutable generation in repository-common
Git config, removes owned worktree-local activation overrides, post-observes
every linked worktree, and reports exact checked, repaired, retained, and
removed paths. Unknown consumers block cleanup rather than being guessed away.

These roots are capabilities, not a fixed lifecycle. `status` selects the sole
current continuation; after an effect, the caller re-observes instead of
replaying a remembered sequence. `adopt` binds an external repository to the
same command semantics; it is not a parallel lifecycle.

## Result Envelope

Every JSON command result uses schema version `2`. `verdict` remains the only
authorization decision; `state` remains the command-state projection; and
`required_gaps` remains the complete blocker list. `next_action` is singular.
`continuation` is derived as `continue`, `await-user`, `blocked`, or `done`;
`missing_facts_or_evidence` derives from `required_gaps` only for
`verdict=unknown`; `user_decision_required` marks the need for user judgment.
These fields are projections, not another lifecycle store.

## Proof Depth

Use a focused gate when one current owner is under review:

```bash
ethos prove --gate <gate-id> --json
```

Use the full local proof plan when the transition requires every configured gate:

```bash
ethos prove --full --json
```

Executed proof is distinct from readiness and binds the result to the expected
head:

```bash
ethos prove --execute --expect-head "$(git rev-parse HEAD)" --json
```

## Hidden Operational Roots

`ethos lane` and `ethos hook` are hidden operational roots. They support Work
Lane admission and guard reporting; they do not expand the public lifecycle.
For a tracked write, bind the exact checkout and paths before editing:

```bash
ethos lane prewrite <paths> --editor-root <worktree> --require-editor-root --json
```

## OpenSpec Ownership

The official OpenSpec CLI owns OpenSpec lifecycle operations. ETHOS consumes
its current facts through `plan`, `prove`, and `land`; it does not re-export the
lifecycle as an ETHOS root.

```bash
openspec list --json
openspec status --change <id> --json
openspec validate --all --strict --json
openspec archive <id> --yes --json
```

## Assurance And Evidence Boundary

Command JSON is machine evidence. A passing readiness result is not an executed
proof, a local publication result is not remote publication evidence, and a
visible Work Lane is not write authority. Semantic ownership and Model Promotion
remain defined only by the canonical Product Design Contract.
