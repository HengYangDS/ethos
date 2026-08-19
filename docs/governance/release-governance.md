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

Required product release surfaces are `README.md`, `LICENSE`,
`CONTRIBUTING.md`, `CHANGELOG.md`, and `.ethos/release.toml`. Hosted forge and
CI files are profile surfaces declared under `.ethos/release.toml`. The
publication topology always contains local verification/install and may declare
zero or more remote peers. Local-only, either one of GitLab or GitHub, and both
remotes are first-class topologies. No absent provider is inferred or required.
The `[publication]` table declares the local repository-native commands;
`[[publication.peers]]` tables declare each peer's ID, provider, role, Git
remote, capabilities, and optional CI surface. A CI surface is required only
when that peer declares `ci_cd`. ETHOS validates that declared paths remain
regular files inside the repository and that local commands are executable; it
never guesses a provider, remote, or tool layout for an adopter.

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
`build/runtime/work/local-install-smoke/`, installs with network access
disabled, verifies that both `ethos` and `ethos` load from that
environment, and exercises the installed CLI help and version surfaces. Its
HEAD-bound receipt lives at `build/evidence/local-install/smoke.json`. This
local proof does not assert registry delivery, remote publication, or hosted
runner success.

The supply-chain owner runs only after the Python wheel exists. Syft `1.50.0`
generates SPDX 2.3 JSON for that exact artifact and the receipt binds its SHA-256,
the SBOM SHA-256, HEAD, and generator version. It deliberately makes no local
provenance, signature, SLSA-level, hosted-CI, or publication claim.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).

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
