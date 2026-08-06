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
`.venv/bin/nox -s runbook_registry` and is not a second command
plane.

See also: [Command Plane](command-plane.md), [Tooling Adoption Roadmap](../plans/tooling-adoption-roadmap.md),
and [Forge Provider Contract](../governance/forge-provider-contract.md).

| ID | Command | Category | Evidence |
| --- | --- | --- | --- |
| RUN-CI-TEMPLATES | `.venv/bin/nox -s ci_templates` | provider-projection | JSON stdout |
| RUN-GITHUB-EMULATOR | `ETHOS_LOCAL_EMULATOR_DRY_RUN=1 tools/ci/scripts/run-github-local-emulator.sh doctor` | provider-emulator | `build/evidence/local-ci/github/doctor.json` |
| RUN-GITLAB-EMULATOR | `ETHOS_LOCAL_EMULATOR_DRY_RUN=1 tools/ci/scripts/run-gitlab-local-emulator.sh doctor` | provider-emulator | `build/evidence/local-ci/gitlab/doctor.json` |
| RUN-FORMAT-SELECTION | `.venv/bin/nox -s format_selection` | format-boundary | JSON stdout |
| RUN-ARCHITECTURE-PROJECTION | `.venv/bin/nox -s architecture_projection` | architecture-projection | JSON stdout |
| RUN-GENERATED-ARTIFACTS | `ethos prove --gate generated-artifacts --json` | generated-artifact-topology | JSON stdout |
| RUN-RELEASE-SUPPLY-CHAIN | `.venv/bin/nox -s supply_chain` | release-supply-chain | `build/evidence/release/supply-chain.json` |

| RUN-DEPENDENCY-HYGIENE | `.venv/bin/nox -s dependencies` | dependency-hygiene | `build/evidence/quality/dependency/summary.json` |
| RUN-PYTHON-VULNERABILITY-AUDIT | `.venv/bin/nox -s vulnerabilities` | security-vulnerability | `build/evidence/quality/security/python-vulnerability-audit.json` |
| RUN-JSON-SCHEMA | `.venv/bin/nox -s schemas` | schema-hygiene | JSON stdout |
| RUN-PROSE-CHECK | `tools/ci/scripts/run-prose-check.sh` | prose | exit code + codespell count |
| RUN-HOSTED-PROVIDER-OBSERVATION | `tools/ci/scripts/run-hosted-provider-observation.sh` | hosted-provider-observation | `build/evidence/hosted-ci/observation.json` |
