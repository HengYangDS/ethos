---
subject: ethos:mechanism-comparison-audit
role: reference
state: active
relations:
  canonical_for: current dmgr, di-effect, and ETHOS mechanism comparison snapshot
  derives_from: docs/plans/tooling-adoption-roadmap.md, docs/governance/product-design-contract.md
---

# Mechanism Comparison Audit

Status: active.

Purpose: preserve the evidence-backed comparison behind the tooling adoption
roadmap so future ETHOS changes can see which dmgr and di-effect mechanisms were
absorbed, deferred, or rejected without turning either reference repository into
ETHOS product truth.

See also: [Tooling Adoption Roadmap](../plans/tooling-adoption-roadmap.md),
[Forge Provider Contract](../governance/forge-provider-contract.md),
[Product Design Contract](../governance/product-design-contract.md), and
[Runbook Registry](runbook-registry.md).

## Snapshot Boundary

This audit is a repository-local reference snapshot taken from current local
checkouts on 2026-07-09:

| Repository | Snapshot label | Role in this audit | Current-state caveat |
| --- | --- | --- | --- |
| dmgr | `dmgr reference checkout` | reference adopter and mechanism source | Domain runtime facts stay adopter-only. |
| di-effect | `di-effect reference checkout` | reference product/tooling source | Its broad policy plane is not imported as an ETHOS command plane. |
| ETHOS | `ETHOS product checkout` | governed product repository | Current truth still comes from source, tests, docs, OpenSpec, claims, evidence, and command JSON. |

The temporary inventory used for this audit was generated outside repository
truth and was not promoted. The durable value here is the classified mechanism
judgment below.

## Verdicts By Mechanism Family

| Mechanism family | dmgr has | di-effect has | ETHOS has now | ETHOS action |
| --- | --- | --- | --- | --- |
| Git lifecycle and closeout | Accepted `dev`, `candidate/dev`, `work/*`, Backlog-aware closeout, retained delivery evidence. | `dev`, `task/*`, `integration/*`, `submit/*`, export and closeout commands. | `status -> plan -> prove -> land -> publish`, Work Lanes, candidate train, accepted-root closeout, lane leases. | Keep ETHOS kernel. Do not import adopter branch names except through profiles. |
| Command runner and environment | Pixi as operator command plane, Nox as broad quality fan-out, Pants graph experiments, just recipes. | Pixi as environment authority, product CLI, Docker gate, just recipes. | uv workspace, Hatchling, `ethos ...`, owner scripts under `tools/ci/scripts/`. | Keep uv/owner-script core. Admit Pixi/Nox/Pants only as adapters. |
| GitHub and GitLab CI | GitLab-centered CI and local GitLab emulation. | GitHub Actions plus GitLab CI, template consistency, local emulators. | GitHub/GitLab templates, tracked projections, CI drift gate, actionlint, local emulator wrappers. | Keep symmetric provider mirror contract; never claim hosted status from local emulators. |
| Local CI emulator | Mature `gitlab-ci-local` doctor/list/dry-run/run/handoff evidence. | `act` and `gitlab-ci-local` emulator configs and matrix paths. | GitHub `act` and GitLab `gitlab-ci-local` wrappers plus local-CI owner bundle. | Adopt minimum emulator contract; deepen handoff and hosted observation later. |
| Format policy | Ruff, markdown, Taplo, Yamllint, SQLFluff routed through Pixi/Nox. | Format-selection policy: TOML for human config, JSON for generated/machine, YAML when tool-native, JSONL for evidence streams. | `.config/checks/format/selection.toml` plus `run-format-selection.sh`. | Keep report-first audit. Add fix modes only after stable ownership. |
| Python lint, type, test | Ruff, ty, pytest, coverage, import-linter, property/perf/mutation/report sessions. | Ruff, mypy, ty, pytest, coverage, docformatter/pydoclint, changed-scope and matrix tests. | Ruff, ty, pytest/coverage, import-linter, docstring coverage, module layout, repository hygiene. | Keep compact hard floor. Add matrix/perf/mutation only for ETHOS product risk. |
| Docs/prose/config lint | Markdown, Vale/codespell, Taplo, YAML/JSON hygiene, docs contracts. | Markdownlint, mdformat, Vale, codespell, DocOS metadata, policy reports. | Markdownlint, Taplo, Yamllint, JSON syntax, docs registry/topology, shell lint. | Prose/DocOS breadth remains maturity debt until owner config, runner, CI projection, and proof exist. |
| Security and dependency hygiene | Gitleaks, dependency audit/deptry patterns, optional Bandit and vulnerability scans. | Gitleaks, Bandit, deptry, pip-audit policy, tool-supply/cache governance. | Gitleaks, Bandit, SBOM, release attestation active; deptry, pip-audit, osv-scanner, grype planned. | Activate dependency/vulnerability gates in separate security lanes. |
| Architecture and C4 | Import boundaries, package topology, Pants graph launcher, semantic-owner/redundancy audits. | Module dependency contracts, architecture graph, LikeC4/C4 stack, generated diagrams. | Import-linter, module-layout, C4-like source, Mermaid projection, architecture drift gate. | Keep lightweight source-to-projection gate; full LikeC4 remains optional. |
| OpenSpec schema/profile | Official OpenSpec workspace plus repo-local SDD lifecycle, claims, evidence, and Superpowers planning. | Official OpenSpec plus repo-local schemas, dynamic facets, capability profiles, provider specs. | Official validation first, then ETHOS lifecycle/schema/profile/claim/evidence checks. | Use official-supported customization; do not fork OpenSpec syntax or `WHEN`/`THEN` semantics. |
| Claims, evidence, chronicle | Rich delivery evidence, closeout logs, parity, retained evidence manifest, prune operations. | `var/` artifact taxonomy, generated metadata, policy reports, evidence sessions. | Claims, chronicle, parity ledger, closeout evidence manifest, local-state audit, proof evidence. | Add retained digest and prune/apply cleanup later; keep evidence classes explicit. |
| Local/generated state | Detailed generated-state grammar, local state audit/clean, Docker hygiene. | `var/` layout, pycache routing, generated docs metadata, cache policy. | Build/evidence/runtime boundaries and local-state audit gate. | ETHOS has invariant, not full operational breadth. Add cleanup fixed point later. |
| Runbook and operator UX | Just recipes and docs for local CI, worktree, proof, Backlog, OpenSpec, closeout. | Large justfile, `di-effect ...` runbooks, generated runbook registry. | `docs/reference/runbook-registry.md` plus registry drift gate. | Keep registry; future generation should come from command registry, not manual tables. |
| MCP and agent projections | MCP/ACP readiness, host probes, official plugin boundaries. | MCP catalog, assembly, runtime targets, materialized overlays. | Agent projection docs, Skills V2, MCP smoke gate. | Keep MCP replaceable and read-mostly; do not make MCP semantic center. |
| Superpowers | Official plugin boundary and planning/review discipline. | External analogue and harness vocabulary, not product kernel. | Adapter-only method-pack entry in tool catalog; no runtime/package dependency. | Optional and replaceable. ETHOS needs equivalent evidence discipline, not Superpowers itself. |
| Task ledger and intake | Backlog task ledger integrated with boards, Work Lanes, claims, and closeout. | Task branch/control-plane concepts; Backlog is not kernel. | Intake/campaign concepts and Backlog-compatible planned adapter. | Keep task ledger adapter-only; Change/Claim lifecycle stays ETHOS-owned. |
| Release and supply chain | Package smoke, deploy smoke, reproducibility, release sessions, GitLab release guidance. | Package/build policy, tool supply, vulnerability and artifact policy. | Local SBOM, release attestation, supply-chain envelope. | External signing/upload/image scanning remain release adapters. |
| Domain runtime | Raw/cache parity, NIO cache, SQL/DolphinDB/getraw, DQC, alphasim compatibility. | Dependency injection, data platform, orchestration, observability, connectors. | Repository governance product only. | Do not absorb domain runtime. Mine adapter, evidence, and parity patterns only. |

## What ETHOS Has More Of

ETHOS is now stronger than the references in these product-governance dimensions:

1. One explicit kernel chain and transition loop instead of a broad helper-command
   surface.
1. Work Lane admission, accepted-root protection, candidate closeout, and
   evidence-bound publication separation as product semantics.
1. OpenSpec as mandatory governance carrier plus ETHOS lifecycle checks, without
   making OpenSpec a second command plane.
1. GitHub/GitLab as symmetric hosted projections over the same owner scripts.
1. Schema-bound command JSON, invalid-state reduction, and proof/report/publish
   separation.
1. Explicit adapter taxonomy for provider, environment, task, agent,
   architecture, release, and adopter-domain mechanisms.

## What ETHOS Has Less Of

ETHOS is deliberately or temporarily lighter in these areas:

1. No Pixi/Nox/Pants operator matrix in core.
1. No Backlog-native task ledger in core.
1. Less full-stack local CI emulator handoff and Docker matrix breadth.
1. Less prose/DocOS metadata breadth.
1. Less dependency and vulnerability gate maturity until deptry, pip-audit,
   osv-scanner, and grype are admitted through owner surfaces.
1. Less MCP assembly/runtime breadth than di-effect.
1. No domain runtime mechanics from dmgr or di-effect.
1. No external signing upload, hosted CI observation capture, image scan, or
   release publication adapter as current truth.

## Adoption Rules

Use these rules when judging future tooling proposals:

1. A mechanism enters ETHOS only as one of: kernel contract, capability profile,
   adapter, evidence class, projection, or quality gate.
1. A tool becomes an active gate only after it has a `system/tools.toml` entry,
   owner config, reusable runner or `ethos ...` surface, provider/hook
   projection, and proof coverage.
1. Local emulators produce local evidence only; hosted success requires hosted
   provider facts.
1. Superpowers, MCP, Backlog, Nox, Pixi, Pants, GitHub, GitLab, Dagger, and
   release/signing tools remain replaceable unless a future accepted decision
   explicitly changes their binding class.
1. Domain runtime mechanisms remain adopter truths; ETHOS may govern them as
   subjects, but does not become them.

## Current Conclusion

The current ETHOS form is suitable for selective adoption, not wholesale tool
import. The right path is to strengthen the evidence and projection surface while
preserving the small product kernel:

```text
absorb mechanism value;
reject adopter ontology drift;
prove active gates before calling them current.
```
