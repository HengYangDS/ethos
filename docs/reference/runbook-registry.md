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
`tools/ci/scripts/run-runbook-registry-check.sh` and is not a second command
plane.

See also: [Command Plane](command-plane.md), [Tooling Adoption Roadmap](../plans/tooling-adoption-roadmap.md),
and [Forge Provider Contract](../governance/forge-provider-contract.md).

| ID | Command | Category | Evidence |
| --- | --- | --- | --- |
| RUN-CI-TEMPLATES | `tools/ci/scripts/run-ci-template-check.sh` | provider-projection | JSON stdout |
| RUN-GITHUB-EMULATOR | `ETHOS_LOCAL_EMULATOR_DRY_RUN=1 tools/ci/scripts/run-github-local-emulator.sh doctor` | provider-emulator | `build/evidence/local-ci/github/doctor.json` |
| RUN-GITLAB-EMULATOR | `ETHOS_LOCAL_EMULATOR_DRY_RUN=1 tools/ci/scripts/run-gitlab-local-emulator.sh doctor` | provider-emulator | `build/evidence/local-ci/gitlab/doctor.json` |
| RUN-FORMAT-SELECTION | `tools/ci/scripts/run-format-selection.sh` | format-boundary | JSON stdout |
| RUN-ARCHITECTURE-PROJECTION | `tools/ci/scripts/run-architecture-projection-drift.sh` | architecture-projection | JSON stdout |
| RUN-GENERATED-ARTIFACTS | `ethos prove --gate generated-artifacts --json` | generated-artifact-topology | JSON stdout |
| RUN-RELEASE-SUPPLY-CHAIN | `tools/ci/scripts/run-release-supply-chain.sh` | built-wheel SPDX SBOM | `build/evidence/release/supply-chain.json` |

| RUN-DEPENDENCY-HYGIENE | `tools/ci/scripts/run-dependency-hygiene.sh` | dependency-hygiene | `build/evidence/quality/dependency/summary.json` |
| RUN-PYTHON-VULNERABILITY-AUDIT | `tools/ci/scripts/run-python-vulnerability-audit.sh` | security-vulnerability | `build/evidence/quality/security/python-vulnerability-audit.json` |
| RUN-JSON-SCHEMA | `tools/ci/scripts/run-json-schema-check.sh` | schema-hygiene | JSON stdout |
| RUN-PROSE-CHECK | `tools/ci/scripts/run-prose-check.sh` | prose | exit code + codespell count |
| RUN-HOSTED-PROVIDER-OBSERVATION | `tools/ci/scripts/run-hosted-provider-observation.sh` | hosted-provider-observation | `build/evidence/hosted-ci/observation.json` |
