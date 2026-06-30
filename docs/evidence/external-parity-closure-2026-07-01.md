---
subject: evidence:external-parity-closure
role: evidence
state: active
relations:
  supports: ethos-external-parity-closure
---

# External Parity Closure Evidence - 2026-07-01

## Scope

This evidence records the batch that made the external ETHOS product command
plane interpret the alphasim-dmgr adopter without relying on the embedded ETHOS
implementation as the default product truth.

Implemented changes:

- `ethos parity shadow` now recognizes Pixi tasks declared in
  `pyproject.toml`, not only `pixi.toml`.
- Shadow parity separates infrastructure failure from command JSON verdicts:
  a command returning exit code `1` with parseable JSON is compared by semantic
  verdict instead of treated as a runner failure.
- The shadow command set now includes `ethos quality command-surface --json`.
- Shadow semantic diff now compares stable dimensions across product and
  embedded schema versions: readiness, required gaps, status role/dirty state,
  planning gates, command-surface verdicts, assistant readiness, playbook route
  readiness, land readiness, publish readiness, and no-push publication
  boundary.
- `ethos quality command-surface --root <adopter>` now honors an adopter
  `rules/ethos/command-surface.toml` policy, including current-doc scan scope
  and historical evidence/archive exemptions.
- `ethos prove --root <adopter>` and `ethos report --root <adopter>` now use an
  adopter governance audit instead of applying ETHOS product package/docs/schema
  requirements to the governed repository.
- `ethos playbooks check|route --root <adopter>` now accepts repo-local skills
  activation records with `name`, `path_globs`, `intent_tokens`, `pre_reads`,
  `post_checks`, and `may_coactivate`.
- `ethos parity gaps --adopter <name>` is now evidence-driven: migration/split
  capabilities close only when tracked parity evidence declares verified
  capabilities and shadow parity reports no required gaps.
- The tracked alphasim-dmgr parity evidence is
  `docs/evidence/parity/alphasim-dmgr-shadow.json`.

## Verification Commands

Focused TDD and regression checks:

```bash
uv run --group dev pytest -q tests/unit/test_parity_command.py
uv run --group dev pytest -q tests/unit/test_parity_command.py tests/unit/test_schema_validation_and_gates.py::test_schema_validation_uses_product_schemas_for_adopter_without_local_schemas tests/unit/test_cli_contracts.py::test_assistants_doctor_accepts_root_for_shadow_parity tests/unit/test_cli_contracts.py::test_playbooks_accept_repo_local_activation_schema_with_path_globs tests/unit/test_cli_contracts.py::test_fleet_inspect_accepts_current_docs_layout tests/unit/test_cli_contracts.py::test_prove_uses_adopter_audit_for_non_product_repo tests/unit/test_cli_contracts.py::test_report_uses_adopter_scorecard_for_non_product_repo tests/unit/test_command_registry_depth.py::test_command_registry_respects_adopter_command_surface_policy
```

Real adopter smoke:

```bash
uv run --package ethos ethos quality command-surface --root /Users/yheng/projects/alphasim-dmgr-fix-b3 --json
uv run --package ethos ethos prove --root /Users/yheng/projects/alphasim-dmgr-fix-b3 --json
uv run --package ethos ethos report --root /Users/yheng/projects/alphasim-dmgr-fix-b3 --json
uv run --package ethos ethos playbooks route --changed --root /Users/yheng/projects/alphasim-dmgr-fix-b3 --json
uv run --package ethos ethos parity shadow --target /Users/yheng/projects/alphasim-dmgr-fix-b3 --execute --timeout-seconds 30 --json
uv run --package ethos ethos parity gaps --adopter alphasim-dmgr --json
```

Observed results:

- Focused parity tests: `12 passed`.
- Full focused regression set: `16 passed`.
- External command-surface against alphasim-dmgr: `ok=true`, no required gaps.
- External proof against alphasim-dmgr: `ok=true`, adopter audit mode, no
  required gaps.
- External report against alphasim-dmgr: `ok=true`, score `7 / 7`, no required
  gaps.
- External playbook routing against alphasim-dmgr: `ok=true`, repo-local skills
  with path glob activation were recognized.
- Real shadow parity against alphasim-dmgr: `ok=true`, `state=matched`,
  required gaps empty across nine public commands.
- Evidence-driven parity gaps for alphasim-dmgr: `ok=true`, `gap_count=0`,
  required gaps empty.
