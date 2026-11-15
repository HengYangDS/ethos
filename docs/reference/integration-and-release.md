---
subject: ethos:integration-and-release
role: reference
state: active
relations:
  part_of: command-plane.md
---

# Integration And Release

This reference answers one reader question: how does source move between a lane, the candidate
and a release, and how does a move that stopped continue? It is part of the command reference: the
[Command Plane](command-plane.md) lists the public commands and their result.

## Native Merge Continuation

`ethos lane refresh-base --strategy merge --json` observes one native merge or prepares a merge from
the configured candidate. The default strategy remains rebase for unpublished replay; a pending
merge instead routes to its own reader. `--mode start|continue|abort` selects one effect. Preview
returns an exact apply command binding HEAD, parents, index, tracked and untracked content, runtime
and Lease generation. Apply requires `--authorize`; a preview is not permission.

For a coordinated peer contribution, `--source-ref refs/heads/work/<lane>` selects an existing Work
Lane for merge strategy, not abort. Preview and apply bind its full ref and exact commit; missing,
non-Work-Lane or changed sources are refused. Continuation requires that source to contain the
recorded pending parent, which remains the commit parent. Default continuation does not assert the
mutable candidate ref. Neither selection updates candidate or protected refs; their integration
remains independent.

Resolve reported conflicts, admit their exact paths and stage the accepted resolution before
requesting `--mode continue`. The shared commit-policy owner checks both parents and the proposed
tree. A common Git CAS advances only the lane; cleanup follows it. Proof, candidate integration and
accepted closeout remain separate obligations. Coexisting official Changes retain separate task
states; ambiguous contributions require explicit resolution, not fabricated completion of incoming
intent. Continue rejects newly authored edits to incoming Change artifacts while preserving the
original parents' native composition; unchanged incoming staged trees authorize no ordinary
cross-Change authoring and claim no incoming task completion. Archiving the local Change retains its
archive attribution instead of selecting an unchanged incoming Change merely because it is still
active.

If a merge CAS completed but its acknowledgement or metadata cleanup did not, inspect returns the
original exact request from its prepared Attestation. It does not mint a new request from the
advanced HEAD or a later selected runtime. Recovery verifies that original plan, parents, index and
metadata against current observations, rechecks the current Lease and runtime, and finishes only the
already observed effect. A preparation whose CAS is unexecuted, ambiguous or unproven remains
UNKNOWN; neither preview nor retry replays its prior CAS.

`--mode abort` does not depend on candidate-ref existence or valid Change compilation. It first
retains affected files, modes, stages and native metadata in content-addressed Git-private recovery
material, then invokes native abort. Native refusal does not justify reset-hard: failure JSON
retains before/after observations, stderr and recovery coordinates. The material is not an automatic
in-place restoration command or a reusable authority grant. Retain unique work until its recovery or
absorption is verified; repeated exact attempts reuse the same content-addressed material rather
than copying the repository.

After lost acknowledgement, retry the same exact request: current authority and state are checked
before recognizing an existing result or finishing its native projection. The ref effect does not
authorize cleanup: Lease/runtime are checked again after CAS. Changed observations reject; unproven
effects remain UNKNOWN. The worktree lock coordinates cooperating writers; it does not isolate
arbitrary same-user processes. Autostash, competing native operations and unsupported multiple merge
parents report a boundary instead of guessing recovery.

## Retained Candidate Materialization

When a candidate ref has advanced but its index and worktree still exactly match
a trusted, retained ancestor, inspect the existing candidate command:

```bash
ethos lane candidate --materialize --preserved-preimage <full-commit-oid> --retention-ref <full-ref> --reason "Restore the retained candidate projection" --root <clean-accepted-root> --json
```

Follow the returned authorized apply command. Its state digest binds the current
candidate and accepted refs, retention ref, common directory, target and actor;
the caller does not restate those facts in another plan. The effect holds native
Git ref assertions, re-observes the exact index and working bytes, and uses the
existing worktree synchronization owner. It moves no ref and replays no earlier CAS.

Unknown edits, untrusted commits, changed refs and ignored or masked overwrite
risks refuse materialization. A completed native effect is recognized without
rewriting its index after a lost acknowledgement. The returned NativeEffect is
evidence of materialization, not source acceptance or a new authorization.

## Accepted Release Selection

For maintenance from a historical accepted base, select `ethos land --release --expect-head
<source-head> --release-base <accepted-base>
--release-head <current-main> --tag v<source-version> --json`. The source must
belong to its native Work Lane, retain the exact accepted-base witness, and have current trusted
signatures, introduced-range admission and a proof bound to the live holder's complete Lease
generation. The base alone authorizes no new source. Only `--apply --authorize` creates the
immutable signed tag; current accepted, candidate, release and maintenance branches remain asserted,
never updated or synchronized. The checkout's branch roles must match current accepted policy.
Publication uses the original completed tag plan and its exact proof and accepted-effect IDs, then
obtains fresh admission independently for each peer.

`ethos land --release --expect-head <accepted-head> --release-head <old-main>
--json` previews selection of the exact current accepted source for an
independent release branch. Add `--tag v<version>` for a declared signed annotated tag. Only
`--apply --authorize` permits the effect. When `.ethos/release.toml` declares
`[release] mirror = "accepted_ff"`, accepted closeout first aligns the protected branches. The same
release command then uses `<accepted-head>` for both exact coordinates and creates the requested tag
without advancing either branch. A misaligned mirror directs the caller to accepted closeout. A
release-tag hook without executor intent directs the caller to this exact release preview.

Selection requires a clean accepted checkout, accepted-effect evidence, current repository proof,
trusted source and safe linked release worktrees. Committed VERSION, package.json or static
pyproject version supplies the native release identity; malformed or conflicting values fail closed.
No duplicate VERSION file is required. One native Git transaction checks accepted and changes the
release/tag refs together. Already aligned branches are assertions, not updates; an aligned request
without a tag has no ref effect or new effect Attestation. Linked checkout synchronization is a
subsequent, explicitly observed effect, not part of Git's ref atomicity.

Interrupted requests retain exact signed objects and the existing TransitionPlan in Git-private
request storage. Recovery rechecks current source, proof, actor, policy and refs. A process lock
serializes cooperating release writers, not arbitrary same-user processes. Unknown signing outcome
never triggers blind resigning; the returned inspection command exposes the retained native object
store. Completed plan persistence makes its staging store disposable. Exact inverse ref intents
permit compensation; arbitrary rollback does not.

A signed release tag whose target a completed signature or history repair replaced is re-created on
the mapped commit with `ethos land --retag <tag> [--original-tag <tag>=<oid>] --json`. The original
tag object comes from the local ref or `--original-tag`; a pruned original is restored from the
repair's backup bundle while that bundle still hashes to its recorded digest. The new object keeps
the original name, tagger, date and message; only its target and signature change. The preview names
each refused tag with its gaps and reports one plan digest for the batch. Only
`--apply --authorize --expect-plan-digest <digest>` moves the tag refs, by exact compare-and-swap
from absent or from the original object, and records one `release:mapped-retag` attestation per tag.
`ethos publish` then qualifies the re-created tag by the proof its original release record embeds.

Delivery of verified accepted source is not another contribution integration. Publication checks its
source, target policy, accepted effect and current proof without reclassifying accepted ancestors as
new contributions. This does not certify historical signatures or pre-adoption compliance.
Independent peers receive the same selected objects through `ethos publish`; local selection is not
remote publication, a Forge Release, deployment or actual user benefit.
