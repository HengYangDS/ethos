---
subject: ethos:runbook-registry
role: reference
state: canonical
relations:
  canonical_for: runnable tooling adoption runbooks
---

# Runbook Registry

Status: canonical.

Purpose: provide a compact registry of reusable local runbooks introduced by the
tooling adoption work. This registry is checked by
`uv run --frozen --offline python -m nox -s runbook_registry` and is not a second command
plane.

See also: [Command Plane](command-plane.md), [Tooling Adoption Roadmap](../plans/tooling-adoption-roadmap.md),
and [Forge Provider Contract](../governance/forge-provider-contract.md).

| ID | Command | Category | Evidence |
| --- | --- | --- | --- |
| RUN-CI-TEMPLATES | `uv run --frozen --offline python -m nox -s ci_templates` | provider-projection | JSON stdout |
| RUN-GITHUB-EMULATOR | `ETHOS_LOCAL_EMULATOR_DRY_RUN=1 tools/ci/scripts/run-github-local-emulator.sh doctor` | provider-emulator | `build/evidence/local-ci/github/doctor.json` |
| RUN-GITLAB-EMULATOR | `ETHOS_LOCAL_EMULATOR_DRY_RUN=1 tools/ci/scripts/run-gitlab-local-emulator.sh doctor` | provider-emulator | `build/evidence/local-ci/gitlab/doctor.json` |
| RUN-FORMAT-SELECTION | `uv run --frozen --offline python -m nox -s format_selection` | format-boundary | JSON stdout |
| RUN-ARCHITECTURE-PROJECTION | `uv run --frozen --offline python -m nox -s architecture_projection` | architecture-projection | JSON stdout |
| RUN-GENERATED-ARTIFACTS | `ethos prove --gate generated-artifacts --json` | generated-artifact-topology | JSON stdout |
| RUN-RELEASE-SUPPLY-CHAIN | `uv run --frozen --offline python -m nox -s supply_chain` | release-supply-chain | `build/evidence/release/supply-chain.json` |

| RUN-DEPENDENCY-HYGIENE | `uv run --frozen --offline python -m nox -s dependencies` | dependency-hygiene | `build/evidence/quality/dependency/summary.json` |
| RUN-PYTHON-VULNERABILITY-AUDIT | `uv run --frozen --offline python -m nox -s vulnerabilities` | security-vulnerability | `build/evidence/quality/security/python-vulnerability-audit.json` |
| RUN-JSON-SCHEMA | `uv run --frozen --offline python -m nox -s schemas` | schema-hygiene | JSON stdout |
| RUN-PROSE-CHECK | `uv run --frozen --offline python -m nox -s prose` | prose | exit code + codespell count |
| RUN-HOSTED-PROVIDER-OBSERVATION | `uv run --frozen --offline python -m nox -s hosted_observation` | hosted-provider-observation | `build/evidence/hosted-ci/observation.json` |
