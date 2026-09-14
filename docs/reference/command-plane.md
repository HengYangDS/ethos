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
| `ethos publish --receipt <path> --receipt-sha256 <digest> --apply --authorize --expect-head <head> --json` | Apply a previously derived full-ref publication request to its declared peers. | Rechecks local trust, target obligations and refs before each peer effect; returns attested partial or unknown outcomes rather than implying cross-peer atomicity. |
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
When activation succeeded but reclamation is incomplete, the result is
`installed_cleanup_deferred`: `data.current` and `summary.wired` retain
the successful activation observation, while `generation_cleanup` reports the
completed removals, retained resources, deferred paths and failure. The overall
verdict remains `block` for incomplete repair. Follow the returned public
`ethos hook install --json` continuation to re-observe and retry; do not undo the
successful activation or delete historical receipts to free their old runtimes.

These roots are capabilities, not a fixed lifecycle. `status` selects the sole
current continuation; after an effect, the caller re-observes instead of
replaying a remembered sequence. `adopt` binds an external repository to the
same command semantics; it is not a parallel lifecycle.

## Accepted Signature Repair

`ethos lane repair-signature --root <accepted-worktree> --expect-head <old-oid>
--json` observes one exact unsigned accepted commit without creating a Git
object, moving a ref, changing a worktree or writing an Attestation. Applying
requires both `--apply` and `--authorize`, plus the current `ETHOS_ACTOR`.

The signed replacement preserves every non-signature payload byte. Current
policy determines selected local refs; unrelated candidates, independent release
refs and remotes remain untouched. CLI recovery and reference-transaction
admission share trusted-source, signer, plan and linked-worktree validation.

Attestations preserve attempted and observed effects, not permission. An
interrupted signing attempt without a durable result remains unknown and cannot
be restarted under another actor. If its exact object has been recovered,
`--replacement <oid>` binds that object for fresh validation without signing
again. Failure JSON retains a known replacement and observes each selected
ref/worktree outcome; lock contention is waiting, not a claimed partial effect.

A successful result gives the exact replacement-bound `ethos prove` command.
It does not prove the replacement, activate a runtime or publish anything.
This operation is not a complete-DAG identity rewrite or a general bypass for
failed admission.

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

Authoring permission and resource retirement are distinct. An explicitly named
local topic ref may retire after exact accepted absorption even if its name is
not `work/*`. Use `ethos lane retire absorbed-ref --branch <branch> --expect-head
<source-oid> --accepted-head <accepted-oid> --root <accepted-root> --json` for an
unlinked, unleased ref; use `ethos lane retire landed --branch <branch>
--expect-head <source-oid> --root <accepted-root> --json` for a clean linked
worktree. First inspect the dry-run and follow its exact authorized apply
command. Existing retirement receipts own partial-effect recovery.

Neither path grants source writes, deletes repository root resources, discards
dirty work, or closes a remote review. Current Lease and exact-object checks
remain in force, and installed hooks require the admitted retirement intent.

Before destructive retirement, stop or drain every actual writer and keep all
participants under lane coordination. Review the resulting final content, then
derive and apply the exact receipt. A Lease transfer or empty process scan does
not itself stop a writer. Active consumers, unknown liveness or changed content
block disposal; re-derive after writer exit if the final content changed. This
protocol does not isolate arbitrary uncooperative same-UID filesystem writes.

For a historical topic with explicitly reviewed staged, unstaged, untracked or
ignored residue, use the existing abandonment owner instead of copying a backup:

```bash
ethos lane retire abandon --branch <source-branch> --reason-code absorbed-semantics --reason '<current semantic owners and disposition>' --review-content --root <accepted-root> --json
```

Derivation records the exact literal tree and index; it does not prove semantic
absorption. Inspect the receipt before using its returned authorized command.
Changed content or authority requires fresh review; interrupted disposal uses
the original receipt and checks surviving content before continuing. Unsupported
native observation blocks; this capability does not imply verified Windows
reviewed-content support.

When one clean historical topic is fully retained by another local topic, derive
retirement without treating that history as accepted product semantics:

```bash
ethos lane retire superseded --branch <source-branch> --expect-head <source-oid> --absorbed-by refs/heads/<retained-branch> --reason '<retention reason>' --root <accepted-root> --json
```

This full-ref form creates the existing immutable retirement receipt and returns
one `lane retire recover` command. Inspect that receipt, then follow its exact
`--receipt`, `--receipt-sha256`, and `--authorize --apply` continuation. Direct
`superseded --apply` with a retention ref is rejected: it would otherwise silently
rebind a moved retained OID. Missing or expired target Lease is admissible; a
valid target Lease requires its current holder. Retained ref movement invalidates
the receipt. Re-derive from current facts instead of replaying stale coordinates.
The surviving ref and checkout are not written, and their unique semantics still
need adjudication before final retirement.

For a registered Work Lane that has lost its Lease, derive coordination recovery
without recreating its checkout or changing its staged and unstaged content:

```bash
ethos lane lease reacquire --path <worktree> --holder-ref "$ETHOS_ACTOR" --root <accepted-root> --json
```

Inspect the exact coordinates and follow the returned authorized apply command.
That command binds the proposed Lease expiry as well as content; replay recognizes
only the exact four-field relation and reuses its existing effect evidence.
An existing foreign or expired Lease requires its own handoff or takeover path;
reacquisition does not overwrite it. The recovered relation does not grant
OpenSpec acceptance or tracked-write permission: obtain fresh prewrite admission
before editing. A partial result identifies a committed Lease separately from
missing effect evidence, so its continuation does not repeat the insertion.

## OpenSpec Ownership

The official OpenSpec CLI owns intent parsing and archive transformations.
ETHOS consumes its facts without becoming a second intent carrier. Commit source
and actual task progress before exact proof. Source acceptance does not require
completing future delivery tasks: the same active Change may remain through
integration, accepted closeout, publication and actual use. Record task
completion only after observing its result; proof does not authorize a later
effect.

After the Change's obligations are settled, an owned Work Lane invokes
`ethos lane archive-change --change <id> --expect-head
<source-head> --json` to derive the bounded official archive and Git transition;
follow its current guarded continuation. Ordinary `git commit` does not replace
that effect owner. A staged official archive still needs valid source proof.
New source bytes invalidate old proof; copied output or repeated commands do
not repair that binding.

```bash
openspec list --json
openspec status --change <id> --json
openspec validate --all --strict --json
ethos lane archive-change --change <id> --expect-head <source-head> --json
```

## Exact Ref Observation For CI

```bash
ethos hook ref-update --target-ref <full-ref> --proposed-head <object-oid> --remote-head <old-object-oid> --remote <name> --root <repository> --json
```

Use the repository-native zero OID for a new ref and `--trusted-baseline <oid>`
when no declared accepted tracking ref supplies the baseline. Both SHA-1 and
SHA-256 coordinates are supported. The command observes the exact introduced
commit range, prior target policy and proposed OpenSpec tree without a host
Lease, proof issuance, local ref changes or remote effects. Deletion has no
introduced range; observation alone never authorizes deletion.

Review targets may carry unfinished intent. Accepted/release targets cannot
use detached checkout identity or a changed candidate declaration to evade
their stronger obligations. Results include `boundary`, `why`, exact coordinates
and a single diagnostic `next_action`; CI consumes the result rather than
copying a parser. For publication effects use the guarded `publish` surface.

## Assurance And Evidence Boundary

Command JSON is machine evidence. A passing readiness result is not an executed
proof, a local publication result is not remote publication evidence, and a
visible Work Lane is not write authority. Semantic ownership and Model Promotion
remain defined only by the canonical Product Design Contract.
