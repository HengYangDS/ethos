---
subject: ethos:governance-platform-evidence
role: evidence
state: active
relations:
  evidence_refs: tests/unit, tests/architecture, OpenSpec, CLI smoke, build, host doctor
---

# ETHOS Governance Platform Evidence - 2026-06-30

## Scope

This evidence records the `ethos-governance-platform` campaign.

Implemented changes:

- Renamed internal package `ethos-adopt` to `ethos-project`.
- Expanded `ethos init/adopt` scaffold to `.ethos`, `.agents/skills`,
  official OpenSpec records, docs, claims, evidence, and hosted CI projections.
- Added `ethos playbooks check|route` and `ethos fleet inspect`.
- Split canonical OpenSpec specs into MECE product families:
  `ethos-kernel`, `ethos-project`, `ethos-governance`, `ethos-workspace`,
  and `ethos-agent`.
- Strengthened self-audit for playbooks, OpenSpec families, schema instances,
  command registry scanning, claims, and self-evolution proof.
- Fixed command-example governance so evidence and archive documents are
  recorded as observational history while current public docs remain enforced
  against retired public roots.
- Propagated retired public-command mentions as actionable `required_gaps`
  through command registry, command-surface, and self-audit reports.
- Completed the active OpenSpec change deltas for projection boundaries,
  self-evolution, official OpenSpec self-governance, and authorized mutation.
- Added standards adapter lifecycle, input/output contract, fallback, and exit
  strategy fields.

## Host Issues Handled

- Fixed the active npm wrapper installation selected by PATH from
  `codex-cli 0.142.3` to `codex-cli 0.142.4` with optional native package
  installed.
- Verified `codex doctor --json` reports fast mode, goals, memories, install
  consistency, and rollout DB parity as ok.
- Fixed the repository pre-commit hook warning by adding a deterministic local
  `.pre-commit-config.yaml` that runs the existing Ruff gate without downloading
  remote hook repositories.
- Remaining host warning: JetBrains provider `/models` route probe returns HTTP
  503 while the provider base URL is reachable. This is classified as a
  provider route/probe compatibility warning, not a repository or npm wrapper
  defect.

## Verification

Commands run from the isolated worktree:

```bash
uv run --group dev pytest tests/unit tests/architecture -q
uv run --group dev ruff check .
openspec validate --all --strict --json
uv build --all-packages
uv run --package ethos ethos self audit --json
uv run --package ethos ethos report --json
uv run --package ethos ethos quality command-registry --json
uv run --package ethos ethos quality command-examples --json
uv run --package ethos ethos quality schemas --json
uv run --package ethos ethos quality standards --json
uv run --package ethos ethos quality release-policy --json
uv run --package ethos ethos quality release-attestation --json
uv run --package ethos ethos quality sbom --json
uv run --package ethos ethos quality commits --enforce-head --json
uv run --package ethos ethos playbooks check --json
uv run --package ethos ethos playbooks route --subject repository-governance --json
uv run --package ethos ethos fleet inspect --target . --json
uv run --package ethos ethos adopt --profile gitlab --dry-run --json
uv run --package ethos ethos prove --execute --gate self-audit --gate claims --gate schemas --json
uv run --package ethos ethos self openspec --change ethos-governance-platform --json
uv run --group dev pytest tests/unit/test_claims_governance.py tests/unit/test_docs_registry.py -q
pre-commit run --all-files
codex --version
codex --strict-config --version
TERM=xterm-256color codex doctor --json
npm ls -g @openai/codex --depth=0
```

Observed results:

- Full unit and architecture suite: `98 passed`.
- Focused scaffold/playbooks/fleet/schema/command-registry suite: `50 passed`.
- OpenSpec strict validation: `7 passed / 0 failed`.
- Ruff: all checks passed.
- Package build: all six packages built successfully, including
  `ethos-project`.
- `ethos report --json`: score `13 / 13`, no required gaps.
- `ethos prove --execute --gate self-audit --gate claims --gate schemas --json`:
  `ok=true`, no required gaps, local proof digest emitted.
- Claims/docs command-example regression: `6 passed`.
- `pre-commit run --all-files`: Ruff local hook passed.
- `codex --version` and `codex --strict-config --version`:
  `codex-cli 0.142.4`.
- `npm ls -g @openai/codex --depth=0`: active npm global package is
  `@openai/codex@0.142.4`.
- `TERM=xterm-256color codex doctor --json`: overall status remains `warning`
  only because the JetBrains provider `/models` route probe returns HTTP 503;
  install, update status, fast mode, goals, memories, state DB integrity, and
  rollout DB parity are ok.
