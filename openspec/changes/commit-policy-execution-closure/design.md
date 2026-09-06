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
trusted baseline. Other zero-remote updates require an explicit trusted baseline
and fail closed without one. A missing endpoint or failed `rev-list` is an
unreadable-range result, never permission to scan from the root.

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

### 6. Treat hooks and hosted jobs as projections

The immutable hook generation expands from three to four launchers. Binding and
activation continue to compare the complete generated set atomically. Status
projects whether policy is declared and whether `commit-msg` and `pre-push` are
the exact current launchers, using the existing hook-install command as the sole
repair action.

GitHub push and pull-request events and GitLab branch and merge-request events
pass their provider-native base/head coordinates to `ethos hook commit-range`.
Manual or observational dispatches with no integration pair do not invoke the
range command and make no range-enforcement claim. Generated provider files
remain byte projections of `.config/ci/templates/hosted/*`.

## Risks / Trade-offs

- **A stale remote-tracking accepted ref could misbound a new proposal range.**
  → The baseline must resolve locally and be an ancestor; publication and CI
  continue to bind exact remote/event coordinates, and unreadable facts block.
- **Signature presence is weaker than signer authorization.** → The distinction
  is explicit: tracked policy governs shape, while lifecycle/publication trust
  remains separately verified and evidenced. No passing report claims signer
  trust unless that verifier ran.
- **Adding `commit-msg` makes an existing runtime generation incomplete.** →
  Status reports the missing launcher and the ordinary immutable `hook install`
  transaction creates and activates a new generation; no generation is edited
  in place.
- **Provider environment variables may be absent for non-integration events.**
  → Templates gate the range command on event kind and never manufacture a
  baseline.

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
