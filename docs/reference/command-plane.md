---
subject: ethos:command-plane
role: reference
state: active
relations:
  projects: ../governance/product-design-contract.md#semantic-kernel
---

# Command Plane

Purpose: explain public ETHOS command behavior and ownership boundaries as an active projection.
The installed CLI command tree owns the exact root inventory.

Canonical owner: [Product Design Contract](../governance/product-design-contract.md#semantic-kernel).

See also: [Quickstart](../guides/quickstart.md),
[Product Design Contract](../governance/product-design-contract.md#semantic-kernel), and
[OpenSpec Governance](../governance/openspec-governance.md).

## Workflow And Transport Roots

The daily workflow and transport operations are:

| Root                                                                                                       | Purpose                                                                                                                                                    | Read or effect boundary                                                                                                                                            |
| ---------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `ethos status --json`                                                                                      | Inspect repository facts, authority, gaps, coordination, and the next action.                                                                              | Read-only projection; does not mint truth.                                                                                                                         |
| `ethos plan --changed --json`                                                                              | Compile the changed-scope TransitionPlan and required gates.                                                                                               | Read-only.                                                                                                                                                         |
| `ethos prove --json`                                                                                       | Check proof readiness.                                                                                                                                     | Read-only unless `--execute` is explicit.                                                                                                                          |
| `ethos land --json`                                                                                        | Report landing readiness.                                                                                                                                  | Effects require the command's explicit guarded options.                                                                                                            |
| `ethos publish --json`                                                                                     | Report local publication readiness.                                                                                                                        | Read-only.                                                                                                                                                         |
| `ethos publish --ref <full-ref> --probe-remote --expect-head <head> --json`                                | Derive an immutable exact-CAS request for one positively admitted branch or annotated release-tag ref from the exact local object and live declared peers. | Read-only; persists only content-addressed request evidence in Git private state.                                                                                  |
| `ethos publish --ref <full-ref> --probe-remote --apply --authorize --expect-head <head> --json`            | Derive and consume the same full-ref publication request.                                                                                                  | Uses the same receipt-bound exact-CAS executor as explicit receipt apply.                                                                                          |
| `ethos publish --receipt <path> --receipt-sha256 <digest> --apply --authorize --expect-head <head> --json` | Apply a previously derived full-ref publication request to its declared peers.                                                                             | Rechecks local trust, target obligations and refs before each peer effect; returns attested partial or unknown outcomes rather than implying cross-peer atomicity. |
| `ethos adopt --root <repo> --json`                                                                         | Plan adoption for one repository.                                                                                                                          | Applying requires explicit authorization and an expected head.                                                                                                     |
| `ethos mcp --root <repo>`                                                                                  | Serve MCP over stdio for one exact repository.                                                                                                             | Tool calls retain native admission; launching the transport grants no authority.                                                                                   |

An exact `publish --ref` request selects every declared peer by default.
Repeat `--peer <declared-id>` to select only named peers. For example:

```text
ethos publish --ref refs/heads/main --peer github --probe-remote --expect-head <head> --json
```

ETHOS still validates the complete declaration but observes and updates only
the selected peer set. The request receipt binds that set; `--receipt` cannot
take a new `--peer` choice. Results distinguish declared, selected, and
unselected peers. A successful selected-peer result does not claim that
another declared peer received the object, and an unavailable peer is never
skipped automatically.

`status`, `plan`, `prove`, `land`, `publish`, `adopt` are workflow roots; `format` and `mcp` are not.
MCP tools project status, planning, adoption and integration over the same typed owners;
it does not yet project every operation. Root and process actor bind at startup.
Strict tool inputs cannot replace either binding. Diagnostics stay on stderr;
stdout is reserved for the protocol. Cancellation and deadline expiry do not
mean rollback: reobserve before retrying an effect. Synchronous work drains
before a queued successor executes; this is not a hard filesystem timeout.

`ethos attestation query` reads exact matches from the sole Attestation set.
`ethos attestation record --input <file>` validates or previews one canonical
record; `--apply` unions it by exact Git CAS. Neither operation grants effect
authority. `ethos lane` and `ethos hook` are operational roots described below,
not extra lifecycles. Native `--help` owns exact syntax; this page explains semantics.

Native formatting uses [the installed formatter operation](../guides/quickstart.md#native-source-formatting), preserving preview/check/apply and runtime selection.

## Shared SDK Operations

`inspect_repository`, `plan_repository`, `adopt_repository` and `land_repository` in
`ethos.domain.inspection`, `ethos.domain.plan`, `ethos.domain.adoption` and
`ethos.domain.land.operation`
return typed `EthosResult` values without CLI rendering or changing the caller's
working directory. Pass an explicit repository path:

```python
from pathlib import Path

from ethos.domain.plan import plan_repository

result = plan_repository(Path("/path/to/repository"), changed=True)
print(result.to_json())
```

Planning reuses current intent resolution, authority, gates and skill activation;
it does not authorize effects. Known native and profile failures retain their
structured results across transports. Operation-specific refusals remain distinct:
an invalid profile blocks observation, while adoption preserves conflicting
authored content rather than overwriting it. Integration keeps candidate, accepted
and release transitions distinct, including preview, exact coordinates and fresh
effect admission. Proof and publication do not yet have equivalent SDK and MCP surfaces.

## Native Python Observer Interface

The native attempt exports `ETHOS_NATIVE_OBSERVER_REQUIREMENT` as the exact
hash-qualified file requirement `ethos @ file://...#sha256=...`, together with
`ETHOS_NATIVE_OBSERVER_RUNTIME_DIGEST`, the selected immutable runtime's 64-hex
digest. The native producer verifies the wheel's SHA256 before child-only
`--no-deps` installation; it does not import or install ETHOS in the Nox parent,
edit adopter metadata or locks, build from source, or select an ambient package.

Run Ruff custody through the installed child, preserving the original Ruff argv:

```text
python -B -I -m ethos.domain.quality.nox run \
  --runtime-output PATH --session ID --configuration PATH \
  -- <exact original Ruff argv>
```

This operation records the actual child interpreter, validates supplied-wheel
PEP 610 provenance, launches Ruff once, and retains its stdout/stderr. It is not
another scheduler or authority. The pytest interface remains
`-p ethos.surface.pytest.plugin`, `--ethos-runtime-output` and
`--ethos-native-session`. Both child records and `execution.json` retain the
observer requirement, runtime digest and wheel SHA256. Supply applies only to
declared Python observer outputs; audit events do not authenticate hostile producers.

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

## Runtime Selection and Recovery

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

To bind an already installed immutable product, use
`ethos hook install --runtime <absolute-runtime-path> --root <repository> --json`.
The selected runtime must match the invoking product and its exact wheel/lock.
Without `--runtime`, a validated immutable package runtime outside another
repository's private Git store is pinned once for a new repository and reused;
source checkouts and foreign private runtimes do not gain this shortcut.
Multiple repositories can reference those same bytes while retaining independent
selectors, hooks and mutable state. The command does not copy external runtime
bytes or grant permission to delete the installation. Ordinary repair reuses a
build-matching complete selection. A complete predecessor remains valid even
when accepted source or its lock advances: installation validates its bytes,
then uses a compatible invoking package or builds a new source-bound generation
before changing the selector. An explicit `--runtime` must match the requested
build. Missing or damaged external supply never triggers an implicit rebuild;
restore the installation or explicitly rebind. A damaged selector also requires
explicit selection. Package-manager upgrade/uninstall qualification is separate.

These are capabilities, not a fixed lifecycle. `status` selects the continuation;
re-observe after effects. `adopt` uses the same semantics, not a parallel lifecycle.

## Accepted Release Selection

For maintenance from a historical accepted base, select
`ethos land --release --expect-head <source-head> --release-base <accepted-base>
--release-head <current-main> --tag v<source-version> --json`. The source must
belong to its native Work Lane, retain the exact accepted-base witness, and have
current trusted signatures, introduced-range admission and a proof bound to the
live holder's complete Lease generation. The base alone authorizes no new source.
Only `--apply --authorize` creates the immutable signed tag; current accepted,
candidate, release and maintenance branches remain asserted, never updated or
synchronized. The checkout's branch roles must match current accepted policy.
Publication uses the original completed tag plan and its exact proof and
accepted-effect IDs, then obtains fresh admission independently for each peer.

`ethos land --release --expect-head <accepted-head> --release-head <old-main>
--json` previews selection of the exact current accepted source for an
independent release branch. Add `--tag v<version>` for a declared signed
annotated tag. Only `--apply --authorize` permits the effect. When
`.ethos/release.toml` declares `[release] mirror = "accepted_ff"`, accepted
closeout first aligns the protected branches. The same release command then
uses `<accepted-head>` for both exact coordinates and creates the requested
tag without advancing either branch. A misaligned mirror directs the caller to
accepted closeout. A release-tag hook without executor intent directs the
caller to this exact release preview.

Selection requires a clean accepted checkout, accepted-effect evidence, current
repository proof, trusted source and safe linked release worktrees. Committed
VERSION, package.json or static pyproject version supplies the native release
identity; malformed or conflicting values fail closed. No duplicate VERSION
file is required. One native Git transaction checks accepted and changes the
release/tag refs together. Already aligned branches are assertions, not updates;
an aligned request without a tag has no ref effect or new effect Attestation.
Linked checkout synchronization is a subsequent,
explicitly observed effect, not part of Git's ref atomicity.

Interrupted requests retain exact signed objects and the existing TransitionPlan
in Git-private request storage. Recovery rechecks current source, proof, actor,
policy and refs. A process lock serializes cooperating release writers, not
arbitrary same-user processes. Unknown signing outcome never triggers blind
resigning; the returned inspection command exposes the retained native object
store. Completed plan persistence makes its staging store disposable. Exact
inverse ref intents permit compensation; arbitrary rollback does not.

Delivery of verified accepted source is not another contribution integration.
Publication checks its source, target policy, accepted effect and current proof
without reclassifying accepted ancestors as new contributions. This does not
certify historical signatures or pre-adoption compliance. Independent peers
receive the same selected objects through `ethos publish`; local selection is
not remote publication, a Forge Release, deployment or actual user benefit.

## Native Merge Continuation

`ethos lane refresh-base --strategy merge --json` observes one native merge or
prepares a merge from the configured candidate. The default strategy remains
rebase for unpublished replay; a pending merge instead routes to its own reader.
`--mode start|continue|abort` selects one effect. Preview returns an exact apply
command binding HEAD, parents, index, tracked and untracked content, runtime and
Lease generation. Apply requires `--authorize`; a preview is not permission.

`--source-ref refs/heads/work/<name>` explicitly selects an existing Work Lane
for merge strategy only. Preview binds its exact source head; apply refuses
source movement. During continuation that source must still contain the recorded
pending parent, which remains the commit parent. Default continuation does not
assert the mutable candidate ref. Neither selection updates candidate or
protected refs; their integration remains independent.

Resolve reported conflicts, admit their exact paths and stage the accepted
resolution before requesting `--mode continue`. The shared commit-policy owner
checks both parents and the proposed tree. A common Git CAS advances only the
lane; cleanup follows it. Proof, candidate integration and accepted closeout
remain separate obligations. Coexisting official Changes retain separate task
states; ambiguous contributions require explicit resolution, not fabricated
completion of incoming intent. Continue rejects newly authored edits to incoming
Change artifacts, while preserving the original parents' native composition. Archiving the local Change retains its archive attribution instead
of selecting an unchanged incoming Change merely because it is still active.

If a merge CAS completed but its acknowledgement or metadata cleanup did not,
inspect returns the original exact request from its prepared Attestation. It
does not mint a new request from the advanced HEAD or a later selected runtime.
Recovery verifies that original plan, parents, index and metadata against current
observations, rechecks the current Lease and runtime, and finishes only the
already observed effect. A preparation whose CAS is unexecuted, ambiguous or
unproven remains UNKNOWN; neither preview nor retry replays its prior CAS.

`--mode abort` does not depend on candidate-ref existence or valid Change
compilation. It first retains affected files, modes, stages and native metadata
in content-addressed Git-private recovery material, then invokes native abort.
Native refusal does not justify reset-hard: failure JSON retains before/after
observations, stderr and recovery coordinates. The material is not an automatic
in-place restoration command or a reusable authority grant. Retain unique work
until its recovery or absorption is verified; repeated exact attempts reuse
the same content-addressed material rather than copying the repository.

After lost acknowledgement, retry the same exact request: current authority and
state are checked before recognizing an existing result or finishing its native
projection. The ref effect does not authorize cleanup: Lease/runtime are checked
again after CAS. Changed observations reject; unproven effects remain UNKNOWN.
The worktree lock coordinates cooperating writers; it does not isolate arbitrary
same-user processes. Autostash, competing native operations and unsupported
multiple merge parents report a boundary instead of guessing recovery.

## Commit Integrity And Accepted History Repair

The repository paradigm owns the commit subject grammar and requires an SSH
signature on every commit, so a repository that tracks no `[commit_policy]` in
`.ethos/workspace.toml` gets that policy. A tracked table may restrict `scopes`
and declare exact `author` and `committer` tables (`name`, `email`); undeclared
identity constraints impose none on other adopters. The common compiler serves
commit-msg, generated commits, replay, pre-push and `ethos hook commit-range`;
there is no separate mutable Git identity policy. Prospective checks use the
index and parent; generated commits use their exact parent and target tree.
Introduced objects must satisfy trusted-baseline policy as well as candidate
constraints. Removing policy cannot waive its own admission.

Signature admission invokes native Git verification against a protected,
repository-external trust anchor. An SSH signature envelope alone is insufficient.
CI supplies trust through its operator-owned environment, never candidate-authored
key material. Identity, signature trust and Forge attribution are separate checks.
Status distinguishes transport arming from signature-trust readiness: missing or
unsafe anchors produce `unready` even when both launchers are installed. A
configured anchor is a prerequisite, not a claim that a particular commit passed
verification or that the Forge recognizes its signer.

Hosted bootstrap accepts `ETHOS_COMMIT_TRUST_ANCHOR` from the operator-managed
runner environment, not a candidate-controlled YAML value. It validates that existing file's external location and
protection, then projects only `gpg.ssh.allowedSignersFile` into the checkout's
local Git config. It never creates keys, changes identities or downloads trust
from the candidate. Omitting the binding does not disable required verification;
the common validator rejects a missing required anchor.

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
For historical corrections, supply `--corrections <json> --reason <text>
--backup <absolute-bundle-path>`. Each exact old OID selects expected and replacement
author/committer fields, `resign: true`, or `remove_attribution_trailers` containing
exact owner-confirmed false `Co-authored-by: Name <email>` trailer lines. Native
Git determines trailer semantics; missing, duplicate or non-attribution selections
reject, and real contributors remain unchanged. Readiness derives affected descendants;
apply also requires the returned `--corrections-sha256`. Duplicate request fields,
symlinked backups and changed requests reject. Recovery validation extracts the
self-contained bundle into an isolated native repository and checks its complete
object closure. Header validation alone does not establish recoverability.

History replacement preserves trees, all unselected message bytes, times, identities and
ordered parent relationships. New signatures attest the repair, not original
authorship. Already-valid same-key re-signing without another change is rejected
before object creation. Interrupted history signing can re-enter the same request:
the owner first finds and verifies existing exact signed payloads, then creates
only missing objects. It does not need another progress database. Ref changes
still use the existing single Git CAS and require fresh admission.

Archive or publication provenance requires the observed ref effect, reconstructed
old-policy scope and a validated object mapping. Reissuing internally consistent
hashes cannot choose a different source policy or arbitrary ref scope. Historical
evidence does not confer current authorization or replace fresh proof. This is a
bounded metadata repair, not permission to change product content or bypass
failed admission. Local records do not establish independence from a writer with
the same operating-system identity; independent verification requires a separate
operator-selected trust boundary.

## Result Envelope

Every JSON command result uses schema version `2`. `verdict` remains the only
authorization decision; `state` remains the command-state projection; and
`required_gaps` remains the complete blocker list. `next_action` is singular.
`continuation` is derived as `continue`, `await-user`, `blocked`, or `done`;
`missing_facts_or_evidence` derives from `required_gaps` only for
`verdict=unknown`; `user_decision_required` marks the need for user judgment.

## Proof Depth

Select a focused gate from its declared owner:

| Option                | Source                        | Selection boundary                                                              |
| --------------------- | ----------------------------- | ------------------------------------------------------------------------------- |
| `--gate <id>`         | Repository-native declaration | The id and its dependencies must be declared.                                   |
| `--product-gate <id>` | Selected ETHOS product        | Explicitly composes that product closure without extending the native registry. |

```bash
ethos prove --gate <native-id> --product-gate <product-id> --json
```

Repeat either option for several roots. Common rules retain product origin;
a same-named native gate cannot replace them. Conflicting descriptors or an id
explicitly selected from both owners refuse. Complete identical dependencies may
share execution. Native default/full/optional membership stays unchanged, and
policy binds origin through execution and issuance.

`ethos prove --full --json` observes the complete configured plan without
execution. Add `--execute --expect-head <head>` for frozen-source evidence.
[Standard verification](#standard-exact-source-proof) owns its acceptance route;
a focused result never implies the complete native floor.

An executed full proof first takes its repository's proof slot, which every worktree shares, then
waits until the host's 1-minute load average is within `ETHOS_PROOF_HOST_LOAD_LIMIT` (default: half
the CPUs; `0` admits on the slot alone). It reports waiting on stderr and waits at most one hour;
longer contention ends the proof with `proof_admission_contended` before any gate runs. The result
records how long admission waited and the load it admitted.

## Hidden Operational Roots

`ethos lane` and `ethos hook` are hidden operational roots. They support Work
Lane admission and guard reporting; they do not expand the public lifecycle.
For a tracked write, bind the exact checkout and paths before editing:

```bash
ethos lane prewrite <paths> --editor-root <worktree> --require-editor-root --json
```

To close the paradigm gaps whose repair follows from their carriers alone,
preview the repairs, then apply them inside the Work Lane:

```bash
ethos lane repair-paradigm --json
ethos lane repair-paradigm --apply --json
```

The preview names each carrier with its diff, the follow-up commands such as a
peer remote rename, and every gap that needs judgment with its canonical repair.
Apply writes only after exact-path prewrite admission and plans nothing on a
repaired tree. It neither runs the follow-up commands nor commits.

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

For independent maintenance, select a full trusted commit OID without changing
the current candidate train:

```bash
ethos lane start <name> --base <full-commit-oid> --holder-ref "$ETHOS_ACTOR" --root <accepted-root> --json
```

Inspect the planned base and follow its exact apply command. Omission of `--base`
retains the candidate default. Both modes use current repository policy, trust,
runtime and Lease authority; an old source does not reactivate old governance.
Creation asserts the observed candidate and writes only the owned lane ref.
Failure compensates only newly created resources. This creates authoring state,
not release authority; exact proof, integration and publication remain separate.

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

## Standard And Fast Verification

Use standard acceptance and scoped iteration; affected contracts and consumers,
not edit size, determine risk. The
[ETHOS source Contributing guide](../../CONTRIBUTING.md#verification "source-only")
is the workflow entry point. The installed CLI and current admission own the
exact required gates; this reference does not create another policy.

### Standard Exact-Source Proof

Start in the owned Work Lane. Bind its existing actor and select the active
Change explicitly when several Changes make intent ambiguous. Check status,
obtain prewrite admission, run focused checks, then commit all non-ignored source
inputs before the exact-source proof:

```bash
ethos status --json
ethos lane prewrite <path> --root <worktree> --editor-root <worktree> --require-editor-root --json
ethos plan --changed --json
ethos prove --full --execute --change <change-id> --expect-head <head> --json
ethos land --json
```

`<head>` is the actual frozen commit, not a branch name. Inspect every terminal
result and follow the current landing continuation; proof does not execute or
authorize landing, installation or publication. Preserve failed reports. Repair
the smallest failing owner before retrying the complete proof. Changing source
bytes, including docs or task progress, requires a new source binding.

### Routine Scoped Execution

Run the repository's original focused tests and formatters first. For a declared
host gate, use the existing product executor without minting a repository proof:

```bash
ethos prove --host --execute --gate <gate-id> --json
```

Omit `--expect-head` for working-tree feedback. Supply it when the check must bind
to a clean frozen source. [Proof selection](#proof-depth) defines native and
product origins for this surface too. Host execution does not issue a proof
Attestation or grant tracked-write or landing authority.

For repository-bound selected proof, use the non-host surface:

```bash
ethos prove --execute --gate <gate-id> --change <change-id> --expect-head <head> --json
```

The policy resolves prerequisites and validates that selection. Passing selected
gates does not satisfy an omitted canonical landing floor. Default proof is not
a universal cheap path: it can still include full unit and coverage obligations.
When default and full policy differ, current acceptance can require full proof.
There is no general automatic risk-selected small-change acceptance or `--fast`
option; use scoped iteration without describing it as completed acceptance.

`--acceptance-purpose local-source` selects the dependency-audit boundary for
local development. It does not skip tests, disable hooks, or authorize CI,
installation, public release or distribution. Runtime reuse avoids redundant
package preparation; it does not reuse unrelated proof or waive fresh effects.

### Authorized Temporary Hook Bypass

Use a temporary bypass only for an explicitly human-authorized operation. Record
the exact repository, operation, reason, skipped checks, recovery coordinates,
owner and exit condition in the existing Change and evidence owner. This is an
emergency path, not the routine fast path or a transferable permission.

Git provides command-scoped hook configuration:

```bash
git -c core.hooksPath="<absolute-empty-hooks-directory>" commit -S -m "<type>: <subject>"
```

Resolve and inspect an actual empty directory on the target platform first.
On POSIX hosts, Git also supports `git -c core.hooksPath=/dev/null <command>`;
`/dev/null` is not a Windows path. The override applies only to that command and
its children; it leaves persistent hook configuration unchanged. Keep the
repository's required signer and identity. Never treat a skipped hook as pass.

`git commit --no-verify` skips its applicable commit hooks, not every hook.
`git push --no-verify` skips local pre-push, not remote protection, status checks
or authorization. Bypassing a Git hook does not disable ETHOS's direct effect
admission or authorize a protected ref update by itself.

After the bounded command, inspect its actual refs, index, worktree and signature
as applicable, then run `ethos status --json` to verify normal arming. Retain
failed evidence and state which proof, installation or publication obligations
remain unproved. A timeout is not rollback: reobserve before retrying. Retire an
owned temporary directory only after checking it is unused and still empty.
Do not write a global hook disable, fabricated proof or permanent waiver.

## Assurance And Evidence Boundary

Command JSON is machine evidence. A passing readiness result is not an executed
proof, a local publication result is not remote publication evidence, and a
visible Work Lane is not write authority. Semantic ownership and Model Promotion
remain defined only by the canonical Product Design Contract.
