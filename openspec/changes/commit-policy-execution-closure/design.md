## Context

See [proposal.md](proposal.md). The existing authority pieces are mostly
present: `.ethos/workspace.toml [commit_policy]` is the only tracked declaration,
`repository.policy.commit.CommitPolicy` is the only compiler, lifecycle commit
creation and refresh consume it, and `validate_commits` already checks replayed
objects. The execution plane is incomplete: no `commit-msg` launcher exists,
pre-push walks a range only for optional configured identity, and hosted
providers do not invoke a repository-owned range admission surface.

The current `validate_commits` also couples the tracked requirement that a
signature exist in a declared format to a machine-local OpenSSH allowed-signers
file. That trust anchor is intentionally external to the repository and is not
available by default on either hosted provider. Treating it as an implicit CI
input would create a hidden requirement; tracking it would recreate the identity
allowlist that the current product contract deliberately removed.

## Goals / Non-Goals

**Goals:**

- close subject and signature-format enforcement before local object creation
  and across every newly integrated commit range;
- make local Git hooks and both hosted providers transport coordinates into one
  package-runtime owner;
- derive one deterministic introduced range and let optional configured identity
  checks consume it rather than walk history again;
- preserve stronger signer-trust verification for ETHOS-created or replayed
  objects;
- make installed enforcement capability visible from status; and
- delete superseded range and module ownership in the same Change.

**Non-Goals:**

- no repository key registry, signer allowlist, historical exception list, or
  provider credential state;
- no claim that `commit-msg` can verify the signature of an object Git has not
  created;
- no change to topology, proof, publication, force-push, or ref-movement
  authority; and
- no AIGW or Proxy source change.

## Decisions

### 1. Keep one declaration and one compiler

`CommitPolicy` remains the only parser and grammar owner. A working-tree caller
loads it from the file, `commit-msg` loads it from the Git index representing the
prospective tree, and post-object admission loads it from the proposed tip's
committed tree. Absence means no additional commit constraint. Any present
malformed table blocks at the consuming boundary.

Alternative rejected: copy the regular expression into shell, GitHub, GitLab,
or a new schema. That creates parallel policy and inevitably drifts.

### 2. Give introduced-range observation one owner

One repository adapter peels each non-delete endpoint to a commit and computes
the oldest-first set reachable from the proposed commit but not from the exact
baseline. A readable non-zero remote object is the baseline even for a
non-fast-forward update; topology separately decides whether that movement is
legal. A new proposal ref derives the declared remote accepted ref as its
trusted baseline. A zero-remote accepted, release, or annotated-tag projection
derives its historical boundary only from the exact accepted-closeout
Attestation selected for the proposed commit. Other zero-remote updates require
an explicit trusted baseline and fail closed without one. A missing endpoint,
missing accepted-closeout effect, or failed `rev-list` is an unreadable-range
result, never permission to scan from the root or trust a sibling ref merely
because it appears in the same push batch.

This supports SHA-1 and SHA-256 by recognizing either native zero width and by
asking Git to resolve and peel objects. Deletions produce an empty, explicitly
classified range. Multiple pre-push updates each receive their own report.

Alternative rejected: reuse `remote..local` without first proving both objects
and the zero-ref baseline. The textual expression is not the defect; implicit or
unreadable coordinates are.

### 3. Separate signature shape from signer trust

The tracked policy can state only whether a signature is required and that its
format is SSH. The shared commit-range validator therefore checks subject,
signature presence, and signature format from immutable commit bytes. It does
not invent signer authorization from those facts.

Lifecycle creation and refresh already possess a local effect boundary and an
external trust anchor. They call the same validator in trust-required mode, so a
created or replayed commit must additionally pass the existing
`verify_commit_trust` owner before repository effects survive. Hosted CI can
enforce the complete tracked declaration without a new key carrier; separate
hosted or publication trust claims continue to require their existing evidence.

Alternative rejected: require an undeclared provider variable or check a
tracked allowed-signers file. The first is hidden authority; the second is a new
repository identity registry.

### 4. Add only the two irreducible transports

`commit-msg` is necessary because `pre-commit` cannot observe the final message.
Its launcher is generated with the existing immutable hook generation and calls
`ethos hook run commit-msg <message-file>`. The Python owner reads the first line,
compiles policy from the index, and returns the same stable subject gap used
after object creation.

`ethos hook commit-range` is necessary because full pre-push admission also owns
proof, topology, and publication concerns that a hosted range check must not
pretend to satisfy. It is a read-only subcommand, accepts only explicit named
coordinates, returns one structured report, and is called by pre-push plus both
native provider templates. It is not a new top-level command, state machine, or
truth store.

### 5. Make physical ownership match semantic ownership

Commit creation/signing and post-object admission have distinct effects and
change reasons, so they form one real semantic package:

```text
src/ethos/adapters/repo/commit/
    __init__.py       declaration only
    creation.py       signer projection and lifecycle object creation
    admission.py      index/tip policy observation, range derivation, validation
```

All current `git_signing.py` consumers move to these concrete modules and the
old module is deleted without a forwarding facade. Configured identity remains
in its own admission module but receives the already-derived revisions; its
private range walker and duplicate ancestry helper are deleted in favor of the
canonical Git adapter.

The product contract's deep-module obligation applies globally. This Change
implements its commit-policy instance, not a new local design rule. The
admission owner keeps index/blob interpretation, endpoint peeling, range walking,
and per-revision aggregation private. One object report owns observation,
subject/signature judgment, and optional trust verification; HEAD audit, object
creation, and range validation consume it. Replay admission accepts exact
candidate/proposed coordinates and the already selected candidate policy, then
owns the complete range validation. Refresh retains rebase effects and
compensation, not the admission algorithm. The explicit policy parameter
preserves authority selection rather than hiding it behind an ambient lookup.

Subject validation remains a public complete invariant because archive previews
and creation both need it before object creation. Hooks and hosted commands
remain thin native transports. Neither public-function count nor source length
decides whether these boundaries are necessary; no facade or new module is
introduced to disguise them.

### 6. Treat hooks and hosted jobs as projections

The immutable hook generation expands from three to four launchers. Binding and
activation compare the complete generated set atomically against the selected
package runtime's own hook contract, not against unaccepted Work Lane source.
Status projects a newer source-only capability as `pending_acceptance` without
asking the incumbent runtime to manufacture a command it does not contain. Once
accepted Git truth advances, the new accepted package owns the ordinary
hook-install transaction and creates a fresh four-launcher generation; no
generation is edited in place.

Hook activation first accepts an already selected immutable runtime only when
its exact build identity, manifest, platform, architecture, dependency-lock
digest, and retained wheel all remain valid. That reuse decision precedes any
attempt to provision another Python image. A matching package runtime therefore
does not become unusable merely because the ambient host interpreter is not an
admissible image source; any lock or identity drift still forces a fresh runtime
build through the normal materialization boundary.

GitHub push and pull-request events and GitLab branch and merge-request events
pass their provider-native base/head coordinates to `ethos hook commit-range`.
Manual or observational dispatches with no integration pair do not invoke the
range command and make no range-enforcement claim. Generated provider files
remain byte projections of `.config/ci/templates/hosted/*`.

### 7. Advance the existing product identity instead of reusing it

`VERSION` remains the only product-version owner. This Change adds observable
commit admission and runtime capability, so acceptance advances the next
prerelease from `0.2.0-alpha.4` to `0.2.0-alpha.5`; npm metadata and the lockfile
remain checked projections. Exact source commit/tree and wheel/runtime digests
continue to distinguish builds within that product identity and do not replace
the user-comparable SemVer value.

Alternative rejected: retain `0.2.0-alpha.4` because source and runtime digests
are unique. That would reuse one product identity for materially different
public behavior and force adopters to compare internal coordinates to discover
the capability boundary.

### 8. Bind shared Node supply to dependencies, not workspace projections

The prepared Node supply contains installed `node_modules/*` dependencies. Its
reuse check therefore compares only those lock entries. Root and linked
workspace records describe source and distribution projections that are not
materialized inside the shared supply; including them makes a product-version
advance falsely invalidate identical dependency bytes and drives unnecessary
installation, cache, and temporary-tree churn.

Alternative rejected: rebuild the shared supply after every workspace version
change. That would conceal an authority error with repeated I/O while producing
the same dependency closure.

### 9. Make bootstrap satisfy the existing interpreter-supply contract

The final package-only acceptance run exposed an existing projection defect:
the local bootstrap synchronized a lock-current `.venv` but did not ensure that
runtime activation could discover a congruent, copyable native Python image.
On macOS, Homebrew's framework Python can own the `.venv` while remaining an
invalid immutable-image source, so offline activation correctly failed even
though dependency provisioning had succeeded.

The existing bootstrap owner now asks the runtime's own image-source admission
whether the synchronized environment already has a valid installed source. It
provisions the exact observed Python version through uv only when that check
fails, then re-runs the same admission before returning. The image lives in uv's
shared managed installation root, not in a test repository or per-run cache;
subsequent bootstrap and every package acceptance remain idempotent and reuse
it. Runtime activation still performs no download, fallback, or compatibility
selection.

Alternative rejected: let hook installation download Python after activation
starts. That would merge toolchain provisioning into repository mutation,
weaken offline determinism, and conceal the missing caller prerequisite.

## Risks / Trade-offs

- **A stale remote-tracking accepted ref could misbound a new proposal range.**
  → The baseline must resolve locally and be an ancestor; publication and CI
  continue to bind exact remote/event coordinates, and unreadable facts block.
- **Signature presence is weaker than signer authorization.** → The distinction
  is explicit: tracked policy governs shape, while lifecycle/publication trust
  remains separately verified and evidenced. No passing report claims signer
  trust unless that verifier ran.
- **Adding `commit-msg` could make candidate source misclassify the accepted
  generation.** → Observation validates the incumbent generation through its
  selected package contract and reports the candidate capability as pending.
  After acceptance, the new package creates and activates a new immutable
  generation; no old package is asked to synthesize unknown launchers and no
  generation is edited in place.
- **Activation could reject a valid selected runtime before comparing it.** →
  Runtime reuse is decided from the selected generation and repository lock
  identity before provisioning. Reuse never weakens manifest, wheel, platform,
  architecture, source, or lock validation.
- **Provider environment variables may be absent for non-integration events.**
  → Templates gate the range command on event kind and never manufacture a
  baseline.
- **A lock-current local `.venv` may be backed by a non-copyable framework
  Python.** → Bootstrap tests the actual runtime admission relation, provisions
  only the exact selected version when necessary, and requires the same check
  to pass afterward; activation itself remains offline and read-only over
  interpreter supply.

## Migration Plan

1. Land the shared range and validator owner, then migrate refresh and optional
   identity admission to it while deleting the old walker and module.
2. Add `commit-msg`, the public commit-range command, and capability projection;
   reinstalling hooks atomically activates the four-launcher generation.
3. Add the same command to both CI templates and regenerate their provider
   projections.
4. Verify raw commit rejection, local bypass defence, hosted-owner invocation,
   all range boundaries, lifecycle trust, status, and projection equality.
5. Archive the official Change only after exact-HEAD proof; activate and read
   back the accepted immutable runtime before retiring the Work Lane.

Rollback is the normal Git reversal of the accepted source followed by
`ethos hook install` from that exact accepted package. Local state requires no
migration because this Change adds no persistent schema.
