## Context

`.ethos/workspace.toml [commit_policy]` already declares subject syntax,
signature requirement, signing format, and two identity fields. Its effective
meaning is fragmented: product audit has a partial TOML reader, the CI bootstrap
has another parser, direct Git object creation treats mutable `commit.gpgsign`
as policy, and refresh forcibly disables signing. The identity fields are even
weaker: no mutation or trust decision consumes them, so a self-referential audit
can pass while the current commit uses an identity outside the configured list.
The result is not merely a refresh bug; it is an authority inversion plus
decorative policy that owns no invariant.

## Goals / Non-Goals

**Goals:**

- Give the tracked commit policy one parser and validator.
- Keep a missing policy optional for generic adopters while failing closed for a
  present malformed policy and allowing the ETHOS self-profile to require it.
- Limit tracked policy to subject syntax, signature requirement, and signing
  format; report Git author and committer identities only as current facts.
- Validate explicit lifecycle subjects before object creation.
- Project tracked signing policy into Git execution and externally verify every
  required object before retaining repository effects.
- Preserve native rebase semantics and exact compensation.
- Remove every superseded reader, schema, helper, and test in the same Change.

**Non-Goals:**

- No signer-probe protocol, process-group extension, signing-agent lifecycle, or
  credential manager.
- No new commit-message template or repository-independent default grammar.
- No replacement for Git rebase, Git signature formats, or the existing trust
  anchor verifier.
- No compatibility import or fallback to mutable Git configuration as policy.

## Decisions

### Compile tracked policy once

One repository-policy module parses `[commit_policy]` into a frozen value used by
audit, Git execution, and lifecycle subject validation. It owns field shape and
regex validity. Callers do not inspect TOML fields themselves.

Absence compiles to no additional commit constraint. This keeps commit policy a
profile-selected repository rule rather than a universal adoption requirement.
The ETHOS repository's own quality profile continues to require and audit its
declared policy. A present table with unknown, mistyped, or invalid fields is a
blocking configuration error.

### Separate policy from execution material

Tracked policy decides whether signing is required and which format is admitted.
Git configuration supplies the local signer program, key, identity, and trust
anchor needed to execute and verify that policy. Ambient `commit.gpgsign` cannot
weaken or strengthen the tracked declaration. The Git adapter projects the
compiled requirement into an exact non-interactive environment and reports
missing or invalid execution material.

### Validate subjects instead of manufacturing universal prose

The compiler validates the first line of an explicit commit message against
`subject_pattern`. A lifecycle operation may offer a semantic default, but it
must validate that candidate before mutation and expose an explicit subject
input when the repository grammar rejects it. The existing standalone
`commit_message.py` helper therefore has no terminal ownership and is removed
after its sole archive consumer migrates.

`identity_mode` and `allowed_identities` are removed rather than migrated. Git
author and committer values, the signing key, signer program, trust anchor,
transport credentials, and forge verification are distinct observations. None
is a tracked permission list, and none may be inferred from another.

### Preserve native rebase and validate its complete output

Refresh continues to delegate replay ordering, conflicts, authorship, and
message preservation to `git rebase`. It passes the policy-derived signing
environment and does not run a speculative signer probe. Git's real operation is
the executable check; failure is captured and compensated through the existing
refresh boundary.

After a successful detached replay, refresh enumerates every commit in the exact
candidate-to-rebased range. Each subject is validated through the compiler and,
when signing is required, each object is checked through the existing Git-object
trust owner. No Work Lane ref, Lease, or final attachment effect is retained
until the complete range passes.

### Delete displaced carriers

Product audit consumes the compiler instead of `load_workspace_commit_policy`.
The current CI jobs do not create commits, so their checkout identity/signing
bootstrap, embedded TOML parser, and all provider/template calls are deleted
without replacement. The unused `commit-policy.schema.json`, its required-schema
entry, the hard-coded message module, dead `commit_git_worktree()` surface,
duplicated policy tests, and rejected signer-probe/process-group tests are
deleted. No forwarding import remains.

The schema gate likewise reuses the repository's existing `jsonschema`-backed
validator instead of spawning a second validator with overlapping ownership.
The product report validates every schema under `system/schemas`; the redundant
`check-jsonschema` development dependency is removed rather than pinned or
silenced around an upstream warning incompatibility.

## Failure And Recovery

- Missing optional policy means no ETHOS-specific subject or signing constraint.
- A present invalid policy blocks before Git mutation with an exact policy gap.
- Invalid subject blocks before object creation.
- Missing signer material or Git signing failure is reported with captured Git
  diagnostics; refresh aborts and restores the original attachment and HEAD.
- Subject or trust failure in any replayed object restores the same pre-state.
- If compensation fails, the result preserves both the primary and compensation
  facts and never claims restoration.

## Verification

Use TDD regressions for optional/malformed policy, rejected identity fields,
tracked policy overriding ambient Git configuration, explicit subject
validation, multi-commit refresh verification, exact zero-residue failure, and
absence of the obsolete CI bootstrap. Then run the focused policy, Git-effect,
refresh, archive, CI projection, schema, reference-closure, module-layout, lint,
formatting, typing, and OpenSpec gates before exact-HEAD proof.
