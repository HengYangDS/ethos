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
`CHANGELOG.md`, `.gitlab-ci.yml`, `.mailmap`, and GitLab issue/MR templates.

Release readiness is proven with:

```bash
uv run --group dev pytest tests/unit tests/architecture -q
uv run --group dev ruff check .
uv build --all-packages
ethos self audit
ethos report
```
