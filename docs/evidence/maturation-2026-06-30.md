---
subject: ethos:product-maturation-evidence
role: evidence
state: active
relations:
  evidence_refs: tests/unit, tests/architecture, CLI smoke, package build
---

# Product Maturation Evidence 2026-06-30

This evidence record covers the ETHOS product maturation campaign.

Implemented scope:

- GitLab-visible project assets: `LICENSE`, `CONTRIBUTING.md`, `CHANGELOG.md`,
  `.gitlab-ci.yml`, `.mailmap`, issue template, and merge request template.
- Commit/signature governance with Conventional Commit checks and SSH signing
  policy, including machine-readable HEAD signature status for release checks.
- JSON Schema validation through `ethos quality schemas`.
- Executable gate registry through `ethos quality gates` and selected
  `ethos prove --execute --gate ...` runs.
- Adoption profiles for generic, Python package, monorepo, GitHub, and GitLab
  repositories.
- Self-evolution ledger and campaign hypotheses loaded from tracked governance
  state.
- MCP server descriptor as an adapter over repository truth.
- Command example validation for current docs and README.

Fresh validation:

```text
uv run --group dev pytest tests/unit tests/architecture -q
result: 74 passed

uv run --group dev ruff check .
result: All checks passed

uv run --package ethos ethos self audit --json
result: ok=true, required_gaps=[]

uv run --package ethos ethos report --json
result: ok=true, score=10/10

uv run --package ethos ethos prove --objective "ethos product maturation" --execute --gate self-audit --gate claims --gate schemas --json
result: ok=true, gate_count=3, runs=[passed, passed, passed]

uv run --package ethos ethos quality release --json
result: ok=true, required_gaps=[]

uv run --package ethos ethos quality schemas --json
result: ok=true, schema_count=18, required_gaps=[]

uv run --package ethos ethos assistants mcp-server --json
result: ok=true, protocol=mcp, transport=stdio

uv run --package ethos ethos adopt --profile gitlab --dry-run --json
result: ok=true, profile=gitlab, planned_files includes .gitlab-ci.yml

uv build --all-packages
result: all six ETHOS packages built as sdist and wheel
```

The final commit for this batch must be signed and verified with:

```bash
ethos quality commits --enforce-head --json
```
