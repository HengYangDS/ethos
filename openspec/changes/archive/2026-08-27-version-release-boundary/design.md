## Context

`VERSION=0.2.0-alpha.1` has already been admitted for source `d36bc9d9...` and a
specific wheel. Later accepted commits therefore cannot reuse that release
identity. The current implementation nevertheless labels any accepted checkout
as an accepted package build, causing `accepted_version_source_conflict` during
normal runtime installation.

## Decision

Build identity contains product version, distribution version, source commit,
and source tree. The normalized distribution version itself distinguishes a
development artifact from an explicit release artifact; no second kind or
channel field is durable. Git role is not package state. Source builds always
use `<next-release>.dev0+g<commit>.t<tree>`; an explicit release transition
alone uses the exact normalized PEP 440 release version and emits a release
Attestation after fresh artifact observation.

`VERSION` advances to `0.2.0-alpha.2`: this changes no stable public API claim;
it identifies the next prerelease target after the already consumed
`0.2.0-alpha.1`. Python projects it as `0.2.0a2`; npm retains canonical SemVer.

Runtime manifest schema changes directly. There is no alias, compatibility
reader, accepted-build branch, or second release state.

Runtime carriers and durable release Attestations have different retention
rules. Old runtime manifests are disposable execution projections and are not
read after the cutover. A previously issued release Attestation is an immutable
semantic root, so the release predicate continues to validate its exact issued
payload schema and normalizes that historical fact into the current four-field
build value. This does not restore the retired fields to current build or
runtime identity.

`CHANGELOG.md` records notable user-facing change groups. It is not a commit log
or publication ledger. Historical headings use canonical product SemVer; local
release facts are described without inventing Git tags or remote publication.

## Rejected alternatives

- Bumping the version only: hides the accepted/release conflation and recurs.
- Retaining both `channel` and `acceptance_state`: duplicates one distinction.
- Treating accepted Git roots as releases: conflates repository integration
  with distribution publication.
- Compatibility readers for the old manifest: preserves the false model.
