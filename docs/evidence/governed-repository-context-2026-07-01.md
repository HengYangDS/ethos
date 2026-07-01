---
subject: ethos:evidence:governed-repository-context
role: evidence
state: active
relations:
  supports: ethos-governed-repository-context
---

# Governed Repository Context Evidence

Status: proven locally.

Purpose: record the local evidence for removing first-class self semantics from
ETHOS governed repository contracts.

## Change

- Replaced the dual-posture governance context with one governed repository
  context.
- Removed the public `ethos self` command group.
- Replaced `self-audit` gate and payload keys with `repository-audit` and
  `repository_audit`.
- Renamed repository audit code, docs, and ledger files away from self-specific
  names.
- Replaced product toolchain binding language so product proof tools remain a
  profile concern rather than a repository role.

## Verification

Completed commands:

```bash
rg -n "ethos self|self_audit|self-audit|self audit|self-governance|self-evolution|self-hosting|single-kernel dual-posture|single_kernel_dual_posture|product_self|adopter_repository|posture" packages docs/governance docs/reference openspec/specs claims README.md tests schemas/ethos .agents/skills
rg -n "ethos self|self_audit|self-audit|self audit|self-governance|self-evolution|self-hosting|single-kernel dual-posture|single_kernel_dual_posture|product_self|adopter_repository|posture" openspec/changes/ethos-skills-v2-quality-governance openspec/changes/ethos-productization-convergence openspec/specs packages docs/governance docs/reference claims README.md tests schemas/ethos .agents/skills
uv run --group dev pytest tests/unit/test_cli_contracts.py::test_playbooks_route_accepts_changed_scope_alias_without_changed_paths -q
uv run --group dev pytest tests/unit tests/architecture -q
uv run --group dev ruff check .
uv run openspec validate --all --strict --json
uv run --package ethos ethos quality claims --json
uv run --package ethos ethos audit --mode shape --json
uv run --package ethos ethos report --json
uv run --package ethos ethos prove --execute --gate repository-audit --gate claims --gate schemas --expect-head "$(git rev-parse HEAD)" --json
```

Results:

- Residual scan found only negative assertions in tests; current product
  packages, docs, OpenSpec specs, claims, README, schemas, and skill activation
  surfaces had no product-facing first-class `self` or `posture` residue.
- Active OpenSpec change scan also found only negative assertions in tests.
- Focus regression: 1 passed.
- Unit and architecture suite: 382 passed in 79.25s.
- Ruff: all checks passed.
- OpenSpec strict validation: 11 items passed, 0 failed.
- Claims quality: ok, no required gaps.
- Repository audit shape mode: ok, no required gaps.
- Report: score 15/15, governance gap count 0, parity pending count 0.
- Proof gates: state `proven`, gate count 3, expected HEAD matched
  `f0869408d4105e7696d32edce27f299c1e4f923b`.

Purpose: preserve local proof commands and the semantic contract changed in this
batch.

See also: [Product Design Contract](../governance/product-design-contract.md),
[Command Plane](../reference/command-plane.md), and
[OpenSpec Governance](../governance/openspec-governance.md).
