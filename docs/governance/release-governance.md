---
subject: ethos:release-governance
role: policy
state: canonical
relations:
  canonical_for: release readiness
---

# Release Governance

A release-ready ETHOS repository must be understandable from tracked source,
license, contribution, changelog, release policy, and evidence files before a
developer opens implementation code.

`VERSION` is the next explicit product-release target. Repository acceptance,
a source development build, and an explicit distribution release are distinct
facts: accepting a Git commit never turns its wheel into the exact release
version. Source builds use unique PEP 440 development identities; only an
explicit release transition may use the exact PEP 440 release projection and
record release Attestation after fresh artifact observation. Product headings
and tags use canonical SemVer; Python package metadata uses its PEP 440
projection.

`CHANGELOG.md` records selected user-facing changes under `Unreleased` and
locally admitted product versions. It is neither a commit log nor evidence of a
Git tag, Forge release, package-registry publication, or hosted CI result. Each
of those remains an independently verified projection.

## Semantic Versioning and Changelog

ETHOS follows [Semantic Versioning 2.0.0][semver] and
[Keep a Changelog 1.1.0][keep-a-changelog]. The public compatibility surface is
the documented CLI arguments, exit codes and structured output, SDK contracts,
MCP tools/resources, configuration, and persisted repository-state contracts.
Private implementation details are not a second public API.

After 1.0.0, incompatible public changes require a major increment;
backward-compatible additions or deprecations require a minor increment;
backward-compatible fixes require a patch increment. Reset subordinate components
as SemVer specifies. Before 1.0.0, the API is explicitly unstable; breaking
changes must still be identified with their migration path. ETHOS uses a minor
increment for an incompatible 0.y.z release line, and numbered prereleases for
iterations toward its explicitly declared target. Unpublished source iterations
do not each require a product-version bump.

ETHOS release spellings are X.Y.Z with optional -alpha.N, -beta.N or -rc.N.
This is an interoperable product-release profile, not the complete SemVer grammar:
other SemVer prerelease identifiers are not thereby invalid under the standard.
Python's PEP 440 spelling is a projection. Source hashes identify development
builds, not chronological release precedence or stable-channel eligibility.

Keep upcoming user-visible changes under Unreleased; at release preparation,
curate them into one exact-version entry with its actual YYYY-MM-DD release date,
newest first. Use nonempty Added, Changed, Deprecated, Removed, Fixed and Security
sections as applicable. Explain compatibility impact and migration, rather than
dump commit subjects. Version and section links must resolve to real history;
do not invent tags, dates, publication or comparisons to fill missing evidence.

Release admission must bind the exact committed version, curated release entry,
signed tag and artifact identities. Reject missing or duplicate target entries,
invalid dates/categories, version disagreement and reuse of released identities
for changed content. Structural validation cannot establish semantic completeness:
review changes to the public contract and their compatibility evidence before
selecting the increment. Historical notes may be corrected transparently, but
released packages, tags and recorded evidence remain immutable.

[semver]: https://semver.org/spec/v2.0.0.html
[keep-a-changelog]: https://keepachangelog.com/en/1.1.0/

## Release Surfaces and Evidence

Required product release surfaces are `README.md`, `LICENSE`,
`CONTRIBUTING.md`, `CHANGELOG.md`, and `.ethos/release.toml`. Hosted forge and
CI files are profile surfaces declared under `.ethos/release.toml`. The
publication topology always contains local verification/install and may declare
zero or more remote peers. Local-only, either one of GitLab or GitHub, and both
remotes are first-class topologies. No absent provider is inferred or required.
The `[publication]` table declares the local repository-native commands;
`[[publication.peers]]` tables declare each peer's ID, provider, role, Git
remote, capabilities, optional API repository URL (`forge_repository`), and CI
surface. The API URL preserves its actual HTTP scheme and port independently
of SSH aliases or transport ports. It contains no credentials. A CI surface is required only
when that peer declares `ci_cd`. ETHOS validates that declared paths remain
regular files inside the repository and that local commands are executable; it
never guesses a provider, remote, or tool layout for an adopter.

Host-private API coordinates may instead live in the existing local Git remote
configuration key `remote.<name>.forgeRepository`. An explicit repository
declaration takes precedence; absent either, an HTTP Git URL supplies its native
repository address. SSH-only transport without API coordinates remains unknown.
Neither this locator nor native client credentials grant deletion authority.

Retire accepted review projections with `ethos publish --retire --ref
refs/heads/proposal/<name> --probe-remote --expect-head <HEAD> --json`, then use
its exact request-receipt action. The same publication owner and pre-push hook
require local and peer accepted absorption plus no open source-branch review.
Valid native history-repair evidence can establish exact old-to-replacement
absorption; patch equivalence cannot. Main release convergence is independent.
GitHub and GitLab use bounded noninteractive native clients; declared plain Git
peers have no Forge review system. Failed or unavailable queries remain unknown.
Each peer is reobserved before exact-old deletion, with partial outcomes and
already-absent replay recorded by the existing publication Attestation.

Release readiness is proven with:

```bash
uv run --frozen --offline python -m nox -s tests
uv run --frozen --offline python -m nox -s lint
uv run --frozen --offline python -m nox -s install_smoke
uv run --frozen --offline python -m nox -s build
uv run --frozen --offline python -m nox -s supply_chain
npm ci --ignore-scripts
npm run ethos -- --version
npm run test:npm
ethos prove --full --json
ethos status --json
```

The commands above are the current product-toolchain toolchain profile for proving
this repository. They do not make `uv`, pytest, Ruff, npm, or a hosted runner
product ontology anchors.

The local installation owner builds the workspace wheels under
`build/artifacts/python/`, creates a fresh environment under
`build/runtime/work/local-install-smoke/`, installs the frozen production
dependency closure there once, installs the wheel into that same environment
without resolving dependencies again, and executes the package lifecycle
exactly once with network access disabled. The installed entrypoint activates a
Git-common runtime; that runtime activates its successor, proves immutable
wheel/source/runtime identity, excludes development dependencies, survives
bootstrap-environment removal, repairs a stale hook projection, starts and
retires a first Work Lane, and recovers a partially completed retirement. The
same run emits the sole HEAD-bound receipt at
`build/evidence/local-install/smoke.json` only after its exact owned transient
root has been removed successfully. Installed runtime and lane commands share
one result-observation boundary that validates the public result and preserves
the exit code and stderr without owning policy. Unit and architecture tests
verify declarations and pure contracts but do not repeat this lifecycle. The
local receipt does not assert registry delivery, remote publication, or hosted
runner success.

The supply-chain owner runs only after the Python wheel exists. The policy-owned Syft release
generates SPDX 2.3 JSON for that exact artifact and the receipt binds its SHA-256,
the SBOM SHA-256, HEAD, and generator version. It deliberately makes no local
provenance, signature, SLSA-level, hosted-CI, or publication claim.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Root](../README.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).

## Publication Boundary

`candidate/dev` and every `work/*` branch are local-only integration state and
MUST NOT be pushed to any declared peer. Remote admission resolves the complete
ref and permits only accepted `dev`, release `main`, `proposal/*`, and signed
annotated tags matching the declared release-tag policy.

The local Git object is the only publication source. A commit or annotated tag
is created and signed once locally; `ethos publish` verifies that exact object,
binds live peer observations into one immutable request, and projects the same
OID to each peer with explicit exact-CAS coordinates. A peer's SSH key, PAT,
OIDC token, account email, or `Verified` presentation is transport or hosted
observation only and cannot rewrite author, committer, tagger, timestamp,
signature, parents, message, or object identity.

Each peer is independently observed, updated, verified, retried, and attested.
One peer's absence or failure does not invalidate local completion or another
peer, and ETHOS never claims cross-peer atomicity. With zero peers it reports
local-only readiness and performs no remote observation. Local proof, candidate
landing, accepted closeout, exact object publication, and hosted CI remain
separate evidence states.
