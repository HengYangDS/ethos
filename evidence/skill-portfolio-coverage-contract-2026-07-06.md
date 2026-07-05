# Skill Portfolio Coverage Contract Evidence — 2026-07-06

## Claim

ETHOS playbook governance now validates skill-portfolio shape as a machine
contract: required primary subjects must exist exactly once, duplicate active
primary ownership is rejected, and `ethos playbooks check --mode v2-strict
--json` exposes the portfolio coverage contract and owner map.

## Repository State

- Work Lane: `work/skill-portfolio-hardening`
- Base accepted/candidate head at lane start: `2b481b12238bc344aa464cde1344575e534e3af6`
- OpenSpec archive: `openspec/changes/archive/2026-07-05-skill-portfolio-coverage-contract`

## Mechanism

- `.agents/skills/activation.toml` declares `[coverage]` with
  `required_primary_subjects` and `single_owner_subjects`.
- `packages/ethos/src/ethos/assistants/playbooks.py` derives active primary
  owners and emits `portfolio_coverage`.
- Strict playbook validation reports deterministic gaps:
  - `skill_portfolio_subject_missing:<subject>`
  - `skill_portfolio_subject_duplicate:<subject>:<ids>`
- `system/schemas/kernel/skill-activation.schema.json` and
  `system/schemas/kernel/skill-registry.schema.json` expose the coverage fields.

## Verification

```text
uv run --group dev pytest tests/unit/cli/test_contracts.py::test_playbooks_commands_expose_repo_local_skills tests/unit/cli/test_contracts.py::test_playbooks_strict_mode_requires_portfolio_primary_subjects tests/unit/cli/test_contracts.py::test_playbooks_strict_mode_rejects_duplicate_primary_subject_owner tests/unit/governance/test_validation_gates.py::test_schema_validation_report_covers_all_ethos_schemas -q
# 4 passed

uv run --group dev ty check packages/ethos/src/ethos/assistants/playbooks.py packages/ethos-core/src/ethos_core/contracts/skill_activation.py
# All checks passed

uv run --group dev ruff check packages/ethos/src/ethos/assistants/playbooks.py packages/ethos-core/src/ethos_core/contracts/skill_activation.py tests/unit/cli/test_contracts.py
# All checks passed

uv run --group dev ruff format --check packages/ethos/src/ethos/assistants/playbooks.py packages/ethos-core/src/ethos_core/contracts/skill_activation.py tests/unit/cli/test_contracts.py
# 3 files already formatted

uv run --group dev openspec archive skill-portfolio-coverage-contract --yes --json
# archivedAs=2026-07-05-skill-portfolio-coverage-contract

ETHOS_ROOT=$PWD uv run --group dev ethos quality projection-drift --json
# ok=true, state=clean, required_gaps=[]
```

## Portfolio Coverage Snapshot

```json
{
  "ok": true,
  "contract": {
    "required_primary_subjects": [
      "repository-governance",
      "change-lifecycle",
      "skill-portfolio",
      "quality-gates",
      "adoption-profile"
    ],
    "single_owner_subjects": [
      "repository-governance",
      "change-lifecycle",
      "skill-portfolio",
      "quality-gates",
      "adoption-profile"
    ]
  },
  "owners": {
    "adoption-profile": ["ethos-adoption-profile-governance"],
    "change-lifecycle": ["ethos-change-lifecycle"],
    "quality-gates": ["ethos-quality-gate-governance"],
    "repository-governance": ["ethos-repository-governance"],
    "skill-portfolio": ["ethos-skill-portfolio-governance"]
  },
  "required_gaps": []
}
```
