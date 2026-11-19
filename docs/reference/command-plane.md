---
subject: ethos:command-plane
role: reference
state: active
relations:
  projects: ../governance/product-design-contract.md#semantic-kernel
---

# Command Plane

This reference projects public commands from the [Product Design Contract](../governance/product-design-contract.md#semantic-kernel).
See [Quickstart](../guides/quickstart.md) for first use. Official OpenSpec owns intent, and the [ETHOS source OpenSpec configuration](../../openspec/config.yaml "source-only") holds its artifact rules.

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
| `ethos publish --receipt <path> --receipt-sha256 <digest> --apply --authorize --expect-head <head> --json` | Apply a previously derived full-ref publication request to its declared peers.                                                                             | Rechecks local trust, target obligations and refs before each peer effect; returns attested partial or unknown outcomes rather than implying cross-peer atomicity. |
| `ethos publish --retire --ref <full-ref> --probe-remote --expect-head <head> --json`                       | Derive an exact retirement request for one proposal or legacy role ref whose content an accepted peer branch contains.                                     | Read-only; the returned receipt action applies it after each peer is re-observed.                                                                                  |
| `ethos publish --observe-hosted --expect-head <head> --json`                                               | Read the hosted runs of the worktree's head on every CI peer, with the jobs that kept a run from passing.                                                  | Read-only; asks each provider's signed-in CLI, records nothing and exits 1 unless every CI peer's runs passed.                                                     |
| `ethos adopt --root <repo> --json`                                                                         | Plan adoption for one repository.                                                                                                                          | Applying requires explicit authorization and an expected head.                                                                                                     |
| `ethos adopt --exit --root <repo> --json`                                                                  | Preview one repository's exit: each key after it, the keys it keeps or leaves, the selectors and generations it removes, its blockers and one digest.      | Read-only; its next action is the exact apply request.                                                                                                             |
| `ethos adopt --exit --apply --authorize --expect-head <head> --expect-plan-digest <digest> --json`         | Apply exactly the previewed exit, or resume an interrupted one: restore the keys ETHOS still owns, then remove the record and the selectors.               | Holds the selection lock and the state transaction, writes a durable receipt first and attempts every compensation step; consumer records stay.                    |
| `ethos mcp --root <repo>`                                                                                  | Serve MCP over stdio for one exact repository.                                                                                                             | Tool calls retain native admission; launching the transport grants no authority.                                                                                   |

An exact `publish --ref` request selects every declared peer by default.
Repeat `--peer <declared-id>` to select only named peers. For example:

```text
ethos publish --ref refs/heads/main --peer github --probe-remote --expect-head <head> --json
```

ETHOS validates all declarations but observes and updates only selected peers.
The receipt fixes that selection; `--receipt` cannot take another `--peer` choice.
Results distinguish declared, selected and unselected peers without silently skipping
unavailable peers or claiming delivery to unselected peers.

`ethos publish --observe-hosted` reads the runs of the worktree's head from every peer that declares
`ci_cd`, through that provider's signed-in CLI (`gh` or `glab`), and lists each run with its
conclusion under `data.hosted_observation`. A run's own conclusion decides it. A run that passed is
one row; a run that failed or still runs also lists its jobs that did not pass, and a failed job
that the provider marks as allowed to fail is `allowed_failure`. The result passes when every CI
peer's runs passed. It blocks with `hosted_run_failed:<peer>` or `hosted_run_missing:<peer>`, and
it is `unknown` with `hosted_run_running:<peer>` or `hosted_run_unknown:<peer>`: a forge that
cannot be read is never a pass. The gaps come in the order that decides the verdict, so the
first names the peer that decided, and the next action is its repair. An unknown peer carries its
own next action under `data.hosted_observation.peers`: the query that failed, or a step by hand.
A repository that declares no CI peer has no hosted plane: the result passes in the state
`no_ci_peer`, and `summary.ci_peers` is 0. The observation is read each time and recorded nowhere.
`ethos land --json` states the same observation of the lane head under `data.hosted_observation`,
and so does the probe of the release branch or a release tag for its proof head. Neither refuses
anything for it; an apply does not read it.

`status`, `plan`, `prove`, `land`, `publish`, `adopt` are workflow roots; `mcp` is transport.
MCP projects status, planning, adoption, integration and publication; proof stays a CLI root.
Root and actor bind at startup and cannot be replaced by tool inputs.
Diagnostics use stderr; stdout carries the protocol. Cancellation or expiry is not rollback:
reobserve before retrying. Synchronous work drains before queued work; filesystem time is not bounded.

`ethos attestation query` reads exact matches from the sole Attestation set.
`ethos attestation record --input <file>` validates or previews one canonical
record; `--apply` unions it by exact Git CAS. Neither operation grants effect
authority. `ethos lane` and `ethos hook` are operational roots described below,
not extra lifecycles. Native `--help` owns exact syntax; this page explains semantics.

Every command but `mcp` runs the one catalog operation (`ethos.contracts.operations`) that its path
and flags select, listed by `ethos [<path>] --help --json` with a group's nested groups by name.
A request that selects none, or sets a flag its operation does not take, runs nothing and exits 2,
as a usage error does; a preview exits 0 on any verdict, an apply, a proof, a publication probe
and a hosted observation exit 1 unless they pass, and an undelivered result exits 3.

`ethos host run [--wait <seconds>] -- <command...>` runs one heavy local command once the host
admits it, and exits with the command's own status; `ethos host status --json` reads the queue.

- **One queue per host.** It sits under ETHOS's host root. Waiters are admitted in arrival order, at
  most the slots that `host.toml` declares, and a holder that exits frees its place with no cleanup.
  A waiter keeps its place behind live holders until `--wait`, at most the declared maximum of
  `timeout.admission_seconds`, then ends with `host_admission_contended:<operation>:<pid>:<since>`
  of the earliest holder, never its path; a record of an older engine names its executable instead.
- **Shared with proofs.** A full proof takes the same host slot after its repository's proof slot;
  a host proof runs its readiness tier without waiting, then holds the ticket, with no repository
  slot and no load wait, for its test and package gates.
- **What the child receives.** `ETHOS_HOST_ADMISSION`, so work that it starts joins the admission;
  `ETHOS_HOST_CPU_CAP` and `PYTEST_XDIST_AUTO_NUM_WORKERS`, one slot's share of the CPUs not
  reserved, at least one, and the cap only lowers a count the environment already declares.
- **The declaration.** `host.toml` declares `slots` (1), `reserved_cpus` (0) and `load_limit` (half
  the CPUs); an out-of-range value is refused, never clamped.
- **The read.** `ethos host status [--guest-cpus <n>] --json` returns the declaration with the
  limit's source, the load and every live ticket, and removes nothing; an owner mark shows only to
  its own repository, and guests above `reserved_cpus` block with the repair that holds them.
- **The work directory.** `--work <name>` marks `build/runtime/work/<name>/` with the run's actor.

## Native CI Projection

[CI Operations](ci-operations.md#native-ci-projection) describes `ethos lane project`.

## Shared SDK Operations

`inspect_repository`, `plan_repository`, `adopt_repository`, `prove_repository`, `land_repository`
and `publish_repository` in `ethos.application.inspection`, `ethos.application.plan`,
`ethos.application.adoption`, `ethos.application.proof.operation`,
`ethos.application.land.operation` and `ethos.application.publication.operation` return typed
`EthosResult` values without CLI rendering or changing the caller's working directory, and refuse
what the CLI refuses. Pass an explicit repository path:

```python
from pathlib import Path

from ethos.application.plan import plan_repository

result = plan_repository(Path("/path/to/repository"), changed=True)
print(result.to_json())
```

Planning reuses current intent resolution, authority, gates and skill activation;
it does not authorize effects. Known native and profile failures retain their
structured results across transports. Operation-specific refusals remain distinct:
an invalid profile blocks observation, while adoption preserves conflicting
authored content rather than overwriting it. Integration keeps candidate, accepted
and release transitions distinct, including preview, exact coordinates and fresh
effect admission. Publication shares one operation across CLI, SDK and MCP. Proof is an application
operation that the CLI and the SDK reach; MCP gains it only once proof gates run in an allow-listed
environment.

## Retained Candidate Materialization

[Integration And Release](integration-and-release.md#retained-candidate-materialization) describes
`ethos lane candidate --materialize`.

## Runtime Selection and Recovery

`status.data.hook_runtime` is the single hook-runtime
inspection surface. It reports installed and expected source commit/tree,
currentness, stable gaps, and the complete `ethos hook install` repair command;
status does not derive a parallel runtime verdict.

Where the accepted branch declares the exact GitHub pin, the selection follows that pin forward
only, and a Work Lane departs from it with `--runtime <R> --reason <text>`. The
[ETHOS source local-state architecture](../architecture/local-state.md "source-only") states
those rules.

`ethos hook install --root <linked-worktree> --json` is one repository-family
repair operation. It activates one immutable generation in repository-common
Git config, removes owned worktree-local activation overrides, post-observes
every linked worktree, and reports exact checked, repaired, retained, and
removed paths. Unknown consumers block cleanup rather than being guessed away.
When activation succeeded but reclamation is incomplete, the result is
`installed_cleanup_deferred`: `data.current` and `summary.wired` retain
the successful activation observation, while `generation_cleanup` reports the
completed removals, retained resources, deferred paths and failure. The overall
verdict remains `block` for incomplete repair. Its continuation is
`ethos status --root <root> --json`, never the installation itself: the
activation holds, status routes the repository to its own next step, and a later
installation retries the reclamation. A refused installation continues the same
way, or to the authorized state reset when only a reset repairs its state. Do not
undo the successful activation or delete historical receipts to free their old
runtimes.

To bind an already installed immutable product, use
`ethos hook install --runtime <absolute-runtime-path> --root <repository> --json`.
The selected runtime must match the invoking product and its exact wheel/lock. Without `--runtime`,
a validated immutable package runtime outside another repository's private Git store is pinned once
into the host store and reused, whether it binds a new repository, upgrades a selection or replaces
a removed package. A repository never selects a package manager's installation in place, which that
manager may leave writable. Source checkouts and foreign private runtimes do not gain this shortcut.
Multiple repositories can reference those same bytes while retaining independent selectors, hooks
and mutable state. The command copies external runtime bytes only into the host store and does not
grant permission to delete the installation. Ordinary repair reuses a build-matching complete
selection. A complete predecessor remains valid even when accepted source or its lock advances:
installation validates its bytes, then pins a compatible invoking package or builds a new
source-bound generation before changing the selector. An explicit `--runtime` must match the
requested build. Missing or damaged external supply never triggers an implicit rebuild; restore the
installation or explicitly rebind. A damaged selector also requires explicit selection. Valid
supplied bytes may repair it without guessing a predecessor location; the result reports unavailable
rollback selection, and a failed cutover restores the exact damaged selector bytes through
compare-and-swap. Package-manager upgrade/uninstall qualification is separate.

`ethos hook retire-supply --scan <root> --json` previews host installations pinned before consumer
records; only `--expect-plan <digest> --apply --authorize` retires that plan. With
`--release-absent` it previews the consumer records whose repository path is absent, and the same
three words release exactly that plan's records; it removes no installation. With
`--release-absent` the grace period is not read. A release that fails in the middle is blocked,
and its result still names the records it released; a planned record whose path was not read
absent again stays, named in `data.not_released` with the reason `present` or `unknown`. A store
that the host cannot look at is a required gap, not an empty plan.

`ethos hook retire-records --json` previews which Git-common store records may retire and writes the
plan of every owned, unnamed record older than its floor; the selected runtime alone runs it, and
only `--expect-plan <digest> --apply --authorize` deletes what that plan and a fresh scan select.
Both previews report bytes against a declared budget in `summary.budget`, as `within` or `over`:
the directories that record retirement owns against `retention.status_bytes`, and the host
store's installations against `retention.host_bytes`. A row whose read missed a place is `unread`
and carries the count in `unread`. A row that is over or unread refuses nothing.

## Accepted Release Selection

[Integration And Release](integration-and-release.md#accepted-release-selection) describes
`ethos land --release` and `ethos land --retag`.

## Native Merge Continuation

[Integration And Release](integration-and-release.md#native-merge-continuation) describes
`ethos lane refresh-base --strategy merge`.

## Commit Integrity And Accepted History Repair

The repository paradigm owns the commit subject grammar and requires an SSH signature on every
commit, so a repository that tracks no `[commit_policy]` in `.ethos/workspace.toml` gets that
policy. A tracked table may restrict `scopes` and declare exact `author` and `committer` tables
(`name`, `email`); undeclared identity constraints impose none on other adopters. The common
compiler serves commit-msg, generated commits, replay, pre-push and `ethos hook commit-range`; there
is no separate mutable Git identity policy. The same checks refuse a whole message that names a
private-class network address by the paradigm's `private_address` pattern, and tag admission refuses
such a tag message. `commit-msg` reads the message above Git's scissors line, and no gap repeats the
address. Prospective checks use the index and parent; generated commits use their exact parent and
target tree. Introduced objects must satisfy trusted-baseline policy as well as candidate
constraints. Removing policy cannot waive its own admission.

Signature admission invokes native Git verification against a protected, repository-external trust
anchor. An SSH signature envelope alone is insufficient. CI supplies trust through its
operator-owned environment, never candidate-authored key material. Identity, signature trust and
Forge attribution are separate checks. Status distinguishes transport arming from signature-trust
readiness: missing or unsafe anchors produce `unready` even when both launchers are installed. A
configured anchor is a prerequisite, not a claim that a particular commit passed verification or
that the Forge recognizes its signer.

`ethos hook bind-trust --json` previews the binding of the commit trust that a CI job's operator
supplies, and `--apply` performs it; a job runs it once before `ethos hook commit-range`. It takes
exactly one input from the operator-managed runner environment, never a candidate-controlled YAML
value: a protected file outside the checkout, named by `--anchor <path>` or by
`ETHOS_COMMIT_TRUST_ANCHOR`, or the public material in `ETHOS_COMMIT_ALLOWED_SIGNERS`, which the
apply writes into a protected temporary file. It validates the file's external location and
protection, then writes only `gpg.ssh.allowedSignersFile` in the checkout's local Git config and
reads it back; the preview names the file and writes nothing. More than one input refuses with
`ci_commit_trust_inputs_ambiguous` and a failed read-back with `ci_commit_trust_projection_failed`;
without an input it binds nothing and reports the state `unbound`. It never creates keys, changes
identities or downloads trust from the candidate. Omitting the binding does not disable required
verification; the common validator rejects a missing required anchor.

`ethos lane repair-signature --root <accepted-worktree> --expect-head <old-oid>
--json` observes one exact unsigned accepted commit without creating a Git
object, moving a ref, changing a worktree or writing an Attestation. Applying requires both
`--apply` and `--authorize`, plus the current actor.

The signed replacement preserves every non-signature payload byte. Current policy determines
selected local refs; unrelated candidates, independent release refs and remotes remain untouched.
CLI recovery and reference-transaction admission share trusted-source, signer, plan and
linked-worktree validation.

Attestations preserve attempted and observed effects, not permission. An interrupted signing attempt
without a durable result remains unknown and cannot be restarted under another actor. If its exact
object has been recovered, `--replacement <oid>` binds that object for fresh validation without
signing again. Failure JSON retains a known replacement and observes each selected ref/worktree
outcome; lock contention is waiting, not a claimed partial effect.

A successful result gives the exact replacement-bound `ethos prove` command. It does not prove the
replacement, activate a runtime or publish anything. For historical corrections, supply
`--corrections <json> --reason <text>
--backup <absolute-bundle-path>`. Each exact old OID selects expected and replacement
author/committer fields, `resign: true`, or `remove_attribution_trailers` containing exact
owner-confirmed false `Co-authored-by: Name <email>` trailer lines. Native Git determines trailer
semantics; missing, duplicate or non-attribution selections reject, and real contributors remain
unchanged. Readiness derives affected descendants; apply also requires the returned
`--corrections-sha256`. Duplicate request fields, symlinked backups and changed requests reject.
Recovery validation extracts the self-contained bundle into an isolated native repository and checks
its complete object closure. Header validation alone does not establish recoverability.

History replacement preserves trees, all unselected message bytes, times, identities and ordered
parent relationships. New signatures attest the repair, not original authorship. Already-valid
same-key re-signing without another change is rejected before object creation. Interrupted history
signing can re-enter the same request: the owner first finds and verifies existing exact signed
payloads, then creates only missing objects. It does not need another progress database. Ref changes
still use the existing single Git CAS and require fresh admission.

Archive or publication provenance requires the observed ref effect, reconstructed old-policy scope
and a validated object mapping. Reissuing internally consistent hashes cannot choose a different
source policy or arbitrary ref scope. Historical evidence does not confer current authorization or
replace fresh proof. This is a bounded metadata repair, not permission to change product content or
bypass failed admission. Local records do not establish independence from a writer with the same
operating-system identity; independent verification requires a separate operator-selected trust
boundary.

## Result Envelope

JSON results use schema version `3`: `verdict` alone decides authorization, `state` projects
command state, `required_gaps` lists every blocker, and `next_action` is singular. Derived
`continuation` is `continue`, `await-user`, `blocked`, or `done`; `missing_facts_or_evidence`
derives from gaps only for `verdict=unknown`. `user_decision_required` identifies needed user
judgment, and `summary.runtime` names the product version, distribution version and source commit
of the committed build that produced the result.

`next` is the step that `next_action` renders, as data, so an agent never parses text:

- `kind` is `command`, `instruction`, `decision` or `done`. A `command` has an `argv`: the exact
  ETHOS invocation to run. A `decision` whose text is one exact ETHOS argv carries it too, as the
  invocation a person approves; no reader runs it without that approval.
- `effects` lists what the argv does, ordered `read`, `remote-read`, `execute`,
  `local-evidence-write`, `local-write`, `host-write`, `remote-write` and `opaque`. An argv takes
  its effects, authority and destructiveness from the catalog operation it selects; `host run`,
  whose argv cannot bound what it runs, and an argv that selects none are `opaque` and destructive.
- `authorization` is the selected operation's authority: `attestation`, `confirm-irreversible`,
  `authorize`, `apply` or `none`, and `human` for a decision or an opaque step.
- `destructive` says whether the argv selects the deletion of something it does not recreate.
  Cleanup that another operation performs under a liveness check is not counted, and that operation
  reports it in its result. A retirement receipt applies only with `--retire`, and a candidate
  refresh that would drop commits accepted lacks needs `--confirm-irreversible`.
- `form` names the catalog operation the argv selects; it is empty for any other step.
- `binding` names the values the argv binds: `root`, `head`, `candidate_head`, `receipt`,
  `plan_digest` and `lease_expires_at`.
- `why` is the first required gap, or else the state.

A gap's code is the text before its first colon, and every code the product raises is
registered in one packaged table, with its owning package and, where the name does not say it, its
meaning and fixed repair. A process exit reads its number from one declared table: `pass` 0,
`blocked` 1, `usage` 2, `undelivered` 3, `process` the child's own status, and `refused` 125
reserved. `ethos --help --json` prints the table as `data.exits`.

Every JSON result fits its budget: 16 KiB, 32 KiB for `plan` or 48 KiB for `help`. A larger result
keeps its wire fields, its own `data` entries of at most 1 KiB and the scalar fields of a larger
mapping, and adds a top-level `bound`. `bound.detail` names the digest-bound artifact of the full
result; `bound` also lists each failing step's id, exit code and first 20 output lines, the entries
it shortened (`partial`) or moved (`moved`), and counts of what it left out.
`ethos.result.expand_result` reads the full result and refuses an artifact whose digest or size
differs, or that disagrees with a field the bound keeps. It returns the result as its producer wrote
it, so ETHOS reads another ETHOS process's result, such as the installed runtime's proof plan, in
full before it reads a moved or shortened field. Detail is a cache, not a receipt: detail older than
seven days is removed whenever new detail is written, and a store that refuses it leaves the result
inline with the reason in `bound.detail_unavailable`. A reader re-derives `next` from `next_action`
and never trusts a carried one; it keeps only a carried step's `inputs`. Each catalog command but
`host run` takes `--actor`, the executor's identity, over `ETHOS_ACTOR`. Without an actor, a
result's `instruction` names the flag in its `inputs`; under another holder, the handoff preview.

## Proof Depth

`ethos prove --execute --gate <id> --expect-head <head> --json` runs one declared gate with its
dependencies; repeat it for several roots. Without `--execute` it reports that gate's readiness
and runs nothing. Every packaged gate runs through a product provider, so it
runs in every repository on the product alone; a repository's own gates come
from its profile or from the registry file its profile names.

`ethos prove --full --json` observes the complete configured plan without
execution. Add `--execute --expect-head <head>` for frozen-source evidence.
[Standard verification](#standard-exact-source-proof) owns its acceptance route;
a focused result never implies the complete native floor.

`ethos prove --readiness --execute --json` runs the readiness gates of the full plan alone and
writes no Attestation. Its `data.unexamined` names what the run did not examine, and it refuses
nothing: `gates` are the planned gates it did not run. On a Work Lane, `tests` maps each test
that reads a path committed since `base`, the candidate branch, to its reason (`changed`,
`conftest`, `imports`, `names` or `stages`), and `unread_paths` lists the changed paths that no
test reads; any other role has an empty `base` and no selection. A renamed file counts as its two
paths. `forge_only_sessions` maps each task-runner session that a step of the pipeline files asks
for, and no planned gate's command does, to its jobs, each named `<pipeline file>:<job>`, and
`forge_jobs` counts the jobs whose commands were read. A session that a step names through a
Forge expression or in quotes is not read, and a GitLab `default` section or hidden template
that holds a script counts as a job of its own name. `unavailable` names a part that could not
be read, with the error: a tracked Python file that is no text, or a pipeline file that cannot
be parsed, makes its part unavailable. A bounded result keeps the field's scalar members,
and the detail that `bound.detail` names holds the rest. The selection is read from tracked text
and is a lower bound: a deleted file selects no test that imported it, and stays under
`unread_paths` unless a test names it. A path of one word also selects every test whose text
holds that word. The caller runs the tests with the native runner. A passing readiness run is
not the full proof's pass and not the Forges' pass.

Full proof first runs its readiness gates, every gate that is not a test or package gate and depends on none, and ends without waiting when one fails. It then holds the repository's shared slot and the host slot, and waits for two consecutive 1-minute load samples within the limit before its test and package gates. The limit is the run's `ETHOS_PROOF_HOST_LOAD_LIMIT` (`0` skips load checks), else `load_limit` in `host.toml`, else half the CPUs. Waiting reports on stderr and stops after one hour with `proof_admission_contended`, which names the load, the limit and its source, before those gates run. Results record wait duration and admitted load. At start or while queued, a lane missing candidate ancestry stops with `candidate_base_stale` and its refresh command; it cannot land.

An executed proof run with a frozen source reports `data.gate_inputs`: `record`, the file of
this run under `gate-results/` in the Git-common store; `compared`, the count of its gates by
the state of their comparison (`agree`, `mismatch`, `open` or `none`); and `attribute_lines`, the
count of effective lines in the Git directory's local attributes file. The record holds the
run's named inputs, where `product` is `tree` when the running product was built from the
proved tree, and for each gate that executed its input `key`, its `statement` (`declared`, `tree`
or `open`), the `comparison` of its verdict with the earlier results of that key and the
committed files that a stated provider `opened` outside its statement. Every gate still runs. A
differing earlier result adds the diagnostic `gate_input_mismatch` at severity `note`, which
names the gate, the key and the earlier result's tree, and changes no verdict; `unavailable`
names the error when the record could not be read or written.

## Hidden Operational Roots

[Operational Roots](operational-roots.md) describes the hidden operational roots `ethos lane`,
`ethos hook` and `ethos release`.

## OpenSpec Ownership

Official OpenSpec owns intent parsing and archive transformations; ETHOS consumes
its facts without duplicating intent. Commit source and observed task progress
before exact proof. Source acceptance does not require future delivery completion:
the active Change may span integration, accepted closeout, publication and use.
Check tasks only after observing results; proof authorizes no later effect.

After the Change's obligations are settled, an owned Work Lane invokes
`ethos lane archive-change --change <id> --expect-head <source-head> --json` to derive the bounded
official archive and Git transition, also for an official archive already staged. Archive needs no
prior proof: follow its guarded continuation, which proves the archived head. If that proof fails,
the same command with `--compensate` and the archived head as `--expect-head` returns the unlanded
archive to its pre-archive head. Ordinary `git commit` does not replace that effect owner. New
source bytes invalidate old proof; copied output or repeated commands do not repair that binding.

```bash
openspec list --json
openspec status --change <id> --json
openspec validate --all --strict --json
ethos lane archive-change --change <id> --expect-head <source-head> --json
```

When several Changes are active, select one per invocation with `--change <id>` on `status`,
`plan`, `prove`, `land` and `lane prewrite`, or with `change` on the MCP `status`, `plan` and `land`
tools: `ethos lane prewrite <path> --change <id> --json`. The option takes precedence over an
inherited `ETHOS_CHANGE` for the whole invocation, including the hooks and other child processes it
starts, and ends with it; the variable remains the fallback. Either input selects intent, never
permission; an empty or unknown value fails closed, and no selector is stored.

## Exact Ref Observation For CI

[CI Operations](ci-operations.md#exact-ref-observation-for-ci) describes `ethos hook ref-update`.

## Standard And Fast Verification

Affected contracts and consumers determine verification, not edit size.
The [ETHOS source Contributing guide](../../CONTRIBUTING.md#verification "source-only") is the workflow entry point;
the installed CLI and current admission select required gates.

### Standard Exact-Source Proof

In the owned Work Lane, bind its actor and select an active Change when intent
is ambiguous. Check status, obtain prewrite admission, run focused checks and
commit every non-ignored source input before exact-source proof:

```bash
ethos status --json
ethos lane prewrite <path> --root <worktree> --editor-root <worktree> --require-editor-root --json
ethos plan --changed --json
ethos prove --full --execute --change <change-id> --expect-head <head> --json
ethos land --json
```

### Exact Index Prewrite

`ethos lane prewrite <paths> --target index --patch <file>` previews disposable native cached checking; bind `--editor-root <worktree> --require-editor-root`. Worktree remains the default. Real Git, worktree and Lease stay unchanged; the expected index tree/digest, HEAD, Lease and patch bind prestate, not the prospective tree.

Scratch objects use the shared store as a read-only alternate and disappear before return. Drift fails closed; split/locked indexes are unknown, and sparse indexes use native cached apply. Preview cannot enforce CAS at later staging; commit admission re-admits actual staged content.

On both targets a patch is read by what Git does with it. A deletion written without its `deleted file mode` line is read as a deletion of its preimage; the empty file that Git then creates at `dev/null` is let be only where that name is free, and a patch that leaves content there is refused. A patch that declares or changes a symbolic link, or declares a submodule entry, is refused. Commit admission differs: it admits a link that native Git staged and does not read what the link names. Request a move by its source and its target.

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

Readiness, execution, local publication and remote publication remain distinct;
Work Lane visibility grants no writes. The Product Design Contract owns semantics.

An independent-verification receipt reaches closeout through
`ethos land --closeout … --independent-verification-receipt <path>` and publication through
`ETHOS_INDEPENDENT_VERIFICATION_RECEIPT`; the
[ETHOS source independent verification guide](../guides/independent-verification.md "source-only")
sets up the provider.
