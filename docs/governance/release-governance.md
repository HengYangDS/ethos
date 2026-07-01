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
CI files are host-profile surfaces declared under `.ethos/release.toml`; the
current product repository uses a GitLab host profile, but GitLab is not a
product release-file requirement.

Release readiness is proven with:

```bash
uv run --group dev pytest tests/unit tests/architecture -q
uv run --group dev ruff check .
uv build --all-packages
npm ci --ignore-scripts
npm run ethos -- --version
npm run test:npm
ethos self audit --mode deep
ethos report
```

The commands above are the current self-hosting toolchain profile for proving
this repository. They do not make `uv`, pytest, Ruff, npm, or a hosted runner
product ontology anchors.
