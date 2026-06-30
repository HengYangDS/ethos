---
subject: ethos:release-governance
role: policy
state: canonical
relations:
  canonical_for: release readiness
---

# Release Governance

A release-ready ETHOS repository must be understandable from GitLab before a
developer opens source files.

Required release surfaces are `README.md`, `LICENSE`, `CONTRIBUTING.md`,
`CHANGELOG.md`, `.gitlab-ci.yml`, and GitLab issue/MR templates.

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

Hosted CI uses Python images for Python package verification and `node:24` for
npm lock, engine, launcher, and pack verification.
