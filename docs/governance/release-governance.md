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

The current release topology is three-layer and peer-complete: local verification
and installation are remote-independent; GitLab and GitHub are complete hosted
repository and CI/CD planes with the same declared repository, CI/CD, update,
and distribution capabilities. GitLab alone remains the organizational primary
publication source. Each provider's observations remain provider-specific:
GitHub success does not prove GitLab publication or GitLab hosted CI, and GitLab
success does not prove GitHub hosted CI or repository proof.

`candidate/dev` remains local-only and must not be pushed to either provider.
The common remote admission whitelist is `dev`, `main`, and `submit/*`; local
pre-push admission enforces it before any provider-specific branch protection.

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
