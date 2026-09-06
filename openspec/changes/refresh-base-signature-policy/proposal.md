## Why

Repository commit policy is currently split across three competing readers:
product audit reads `.ethos/workspace.toml`, Git object creation infers whether
signing is required from mutable `commit.gpgsign`, and CI parses the TOML again.
`ethos lane refresh-base` then overrides Git with `commit.gpgSign=false`. This
allows ambient configuration to weaken tracked policy, lets generated subjects
bypass the repository grammar, and gives refresh no trustworthy rule for the
objects it replays.

## What Changes

- Compile optional `[commit_policy]` from `.ethos/workspace.toml` through one
  repository-policy owner. Absence adds no generic adopter constraint; a present
  malformed policy fails closed.
- Validate every ETHOS-generated commit subject through that owner. An operation
  may propose a default only when it satisfies the declared pattern; otherwise
  it requires an explicit valid subject instead of emitting a universal message.
- Project a declared signing requirement into Git execution rather than deriving
  policy from mutable Git configuration. Keep signer/key execution details in
  the Git adapter and object trust in the existing Git-object verifier.
- Delete `identity_mode` and `allowed_identities`: they do not authorize a
  mutation or establish signature trust, and Git author/committer identity
  remains an observed repository fact rather than a tracked allowlist.
- Let native rebase report real signer failure, verify every newly replayed
  commit against the tracked subject and signature policy before any ref or
  Lease effect, and restore the exact pre-state on failure.
- Delete the CI checkout identity/signing bootstrap and its embedded TOML
  parser because the current jobs do not create commits. CI verifies existing
  objects through the repository gates; it does not manufacture a temporary
  signer merely to satisfy a self-audit.
- Delete the displaced policy loader, hard-coded lifecycle-message owner,
  unused report schema, duplicated tests, and rejected signer-probe/process-group
  experiment.
- Reuse the product's existing `jsonschema` validator for the complete schema
  tree and delete the redundant `check-jsonschema` command dependency.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: Generated lifecycle commits consume one tracked commit-policy
  compiler and cannot bypass its subject or signing requirements.
- `repository-governance`: Repository audit, CI setup, refresh replay, and Git
  object verification agree on the same tracked policy and exact object facts.

## Impact

The repository commit-policy compiler, Git signing projection, archive commit
input, refresh orchestration, schema validation gate, CI projections, and their
focused tests change. No signer-probe protocol, policy schema, compatibility
facade, persistent state, or adopter-specific carrier is introduced.
