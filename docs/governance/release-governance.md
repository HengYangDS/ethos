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
CI files are profile surfaces declared under `.ethos/release.toml`; they are
not product release-file requirements.

The current release topology is three-layer and dual-remote: local verification
and installation are remote-independent; GitLab is the organizational primary
publication source; GitHub is an independent mirror for update and
distribution. An available GitHub mirror during a GitLab outage does not prove
GitLab publication, GitLab hosted CI, or repository proof.

Release readiness is proven with:

```bash
tools/ci/scripts/run-python-tests.sh
tools/ci/scripts/run-python-lint.sh
uv build --all-packages --out-dir build/artifacts/python --clear --no-create-gitignore
npm ci --ignore-scripts
npm run ethos -- --version
npm run test:npm
ethos audit --mode deep
ethos report
```

The commands above are the current product-toolchain toolchain profile for proving
this repository. They do not make `uv`, pytest, Ruff, npm, or a hosted runner
product ontology anchors.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
