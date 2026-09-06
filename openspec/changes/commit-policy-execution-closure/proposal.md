## Why

ETHOS already has one tracked commit-policy declaration and one compiler, but
ordinary Git commits and newly integrated push ranges can bypass its subject and
signature requirements. The missing execution closure forces adopters to copy
parsers into hooks or forge jobs and makes policy conformance depend on which
transport happened to create or publish an object.

## What Changes

- Reuse the existing `[commit_policy]` compiler and commit validator as the
  single semantic owner for local hooks, push admission, CI, and
  ETHOS-generated lifecycle commits.
- Install a package-runtime `commit-msg` hook that validates the final message
  subject before object creation; it does not claim to validate a signature
  that does not yet exist.
- Derive the exact commits introduced by each non-delete push update and apply
  the same subject and required-signature validation after object creation.
  Ordinary fast-forwards use the observed remote tip; new proposal refs use the
  trusted accepted baseline; a zero remote without a trustworthy baseline fails
  closed; non-fast-forward updates validate the commits newly reachable from the
  proposed tip while the existing topology and ref policy continue to decide
  whether the ref movement itself is allowed.
- Treat signature presence and declared format as commit-policy facts. Signer
  trust remains an operation-specific external observation, so hosted runners do
  not need a new tracked key registry and local lifecycle mutation retains its
  stronger trust check.
- Expose one JSON admission/report surface that local pre-push and native
  GitHub/GitLab jobs consume without copying regular expressions, range walking,
  or state-machine logic.
- Report whether the commit-message transport and pushed-range enforcement are
  armed. A missing policy adds no constraint; a present malformed policy fails
  closed.
- Delete or absorb the duplicate push-range walker after all identity, subject,
  and signature checks consume one exact integration-range projection.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: Commit policy is enforced for newly created local
  messages and exactly the commits introduced by a proposed integration.
- `command-plane`: Hook/status/report surfaces expose one executable,
  machine-composable commit-policy admission result.
- `adapters`: Git hooks and forge/CI projections invoke the same repository
  owner and do not duplicate policy parsing or range semantics.

## Impact

The repository commit-policy validator, Git range observation, hook runtime and
activation, pre-push admission, repository status/audit projection, native CI
owner commands, and focused tests change. No adopter schema, historical
exception list, compatibility layer, persistent state, or second parser is
introduced.
