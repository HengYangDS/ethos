---
subject: ethos:evidence:hooked-write-admission
claim: ethos-hooked-write-admission
date: 2026-07-02
role: evidence
state: active
relations:
  canonical_for: hooked write admission evidence
---

# Hooked Write Admission Evidence

This evidence record covers the hooked write admission Work Lane in the
terminal OpenSpec productization campaign.

## Claim

ETHOS exposes hook-time write admission that binds pre-tool and mutation-risk
pre-run decisions to Work Lane prewrite, reports context-bound mutation fields,
and fuses protected-root or unexpected-path post-write drift.

## Scope

- Added `ethos_adapters.hook_admission` as the product hook admission report.
- Added `ethos hook admit` as a maintainer/reference command.
- Added hook admission tests for context, pre-tool, pre-run, protected-root
  post-write drift, and unexpected Work Lane post-write drift.
- Updated command registry, command-plane docs, OpenSpec deltas, and campaign
  manifest state.

## Recovery Note

During this lane, an initial patch command wrote a new untracked OpenSpec
directory to the accepted root because the patch tool did not carry a worktree
root. Recovery copied the untracked directory into the admitted Work Lane and
removed the untracked accepted-root directory. The accepted root returned to a
clean `git status --short` before product implementation continued.

## Verification Command Set

Commands run from `/Users/yheng/projects/ethos-work-hooked-write-admission-runtime`:

```bash
uv run --group dev pytest -q tests/unit/test_hook_admission.py tests/unit/test_cli_contracts.py::test_hook_admit_pre_tool_blocks_accepted_root tests/unit/test_cli_contracts.py::test_hook_admit_pre_run_blocks_mutation_risk_without_paths tests/unit/test_command_registry_depth.py::test_hook_admission_is_reference_command_not_public_workflow
uv run --group dev pytest -q tests/unit/test_evolution_ledger.py tests/unit/test_schema_validation_and_gates.py::test_campaign_schema_accepts_lane_closeout_steps tests/unit/test_cli_contracts.py::test_campaign_status_reports_manifest_steps tests/unit/test_hook_admission.py tests/unit/test_cli_contracts.py::test_hook_admit_pre_tool_blocks_accepted_root tests/unit/test_cli_contracts.py::test_hook_admit_pre_run_blocks_mutation_risk_without_paths tests/unit/test_command_registry_depth.py::test_hook_admission_is_reference_command_not_public_workflow
uv run --group dev pytest -q
uv run --group dev ruff check .
uv run openspec validate --all --strict --json
uv run --package ethos ethos openspec --lifecycle --json
uv run --package ethos ethos quality schemas --json
uv run --package ethos ethos quality claims --json
uv run --package ethos ethos report --json
uv run --package ethos ethos prove --execute --expect-head "$(git rev-parse HEAD)" --json
uv build --all-packages
```

The initial full test run exposed this evidence file's incomplete front matter
and missing claim digest. This record and
`claims/ethos-hooked-write-admission.toml` were repaired before final closeout
verification.
