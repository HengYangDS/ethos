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
publication topology has three layers: local verification/install, GitLab
organization collaboration, and GitHub public distribution. GitLab and GitHub
are independent forge authority planes. A maintainer may select one configured
remote for a bounded publication when the other is unavailable, but that choice
does not assert synchronization, hosted CI success, or authority precedence.
The `[publication]` table explicitly declares both local repository-native
commands and each provider's CI surface. ETHOS validates that all paths remain
regular files inside the repository and that local commands are executable; it
never guesses ETHOS's own script or workflow layout for an adopter.

Release readiness is proven with:

```bash
.venv/bin/nox -s tests
.venv/bin/nox -s lint
.venv/bin/nox -s install_smoke
.venv/bin/nox -s build
.venv/bin/nox -s supply_chain
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
MUST NOT be pushed to either declared remote. Remote admission is explicit by
remote name and permits only `dev`, `main`, and `proposal/*`. `ethos publish`
observes each configured remote independently and never pushes or claims hosted
CI success; local proof, candidate landing, accepted closeout, and each remote
publication remain separate evidence states.

When local closeout is complete and GitLab is unavailable, a non-force push of
the accepted `dev` and release `main` heads to configured GitHub is permitted
after GitHub's own ordinary dry-run and hook admission. Campaign terminal
source-budget progress remains visible as advisory state; it is still required
for full proof and global compression closeout, not a substitute for the
per-head proof and accepted-closeout gates.
