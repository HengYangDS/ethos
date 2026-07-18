---
subject: ethos:complete-implementation-roadmap
role: plan
state: planned
relations:
  canonical_for: integrated implementation roadmap
  refines:
    - docs/plans/tooling-adoption-roadmap.md
    - docs/reference/mechanism-comparison-audit.md
    - docs/governance/forge-provider-contract.md
    - docs/governance/openspec-governance.md
---

# Complete Implementation Roadmap

Status: planned.

Purpose: sequence the implementation program for forge parity, local CI
emulation, OpenSpec governance, method-pack boundaries, quality/tooling,
architecture projection, and adopter-profile validation without turning planned
material into accepted repository truth.

This roadmap is a plan carrier. It does not replace the narrower
[Tooling Adoption Roadmap](tooling-adoption-roadmap.md),
[Mechanism Comparison Audit](../reference/mechanism-comparison-audit.md),
[Forge Provider Contract](../governance/forge-provider-contract.md), or
[OpenSpec Governance](../governance/openspec-governance.md). Each work slice
becomes truth only after promotion into source, tests, package metadata,
canonical governance/reference docs, accepted decisions, OpenSpec records,
claims, evidence, or HEAD-bound command JSON.

## Target Shape

ETHOS remains a Git-native governed repository kernel. External systems are
adapters, projections, sensors, or execution backends; none of them becomes the
repository authority.

The target shape is:

1. **One kernel, multiple forge projections**: GitHub and GitLab are repository
   carriers over the same Git truth, branch roles, gates, templates, provider
   observations, and publication boundary.
2. **Local CI emulation as bounded evidence**: local GitHub/GitLab emulators
   can prove provider-template shape and local reproducibility, but they never
   claim hosted CI success.
3. **Official OpenSpec first**: OpenSpec official workspace and validation stay
   first; ETHOS adds official-compatible schema/profile checks after official
   validation, not a forked schema dialect.
4. **Method packs remain replaceable**: Superpowers and similar skills can
   improve human/agent discipline, but ETHOS truth is source, tests, schemas,
   OpenSpec, evidence, claims, and command JSON.
5. **Quality and architecture stay owner-scripted**: format, lint, type, tests,
   security, supply chain, architecture projection, and C4/Mermaid drift checks
   run through owner scripts and `system/tools.toml`.
6. **Adopter parity is empirical**: profile behavior is validated by real
   shadow/parity runs against adopter repositories, not by analogy.

## Accepted-Head Baseline

These baseline observations describe the accepted ETHOS product shape at the
head that admits this document. They are navigation aids, not permanent claims;
re-check the named evidence surfaces on the HEAD under review.

| Area | Accepted-head observation | Evidence surface |
| --- | --- | --- |
| Forge parity | GitHub/GitLab CI templates, provider templates, hosted observation script, and local emulator scripts are modeled as forge projections. | `docs/governance/forge-provider-contract.md`, `.config/ci/templates/**`, `tools/ci/scripts/run-*-emulator.sh`, `tools/ci/scripts/run-hosted-provider-observation.sh` |
| Tool catalog | Active, candidate, deferred, and rejected tools are cataloged rather than inferred from host availability. | `system/tools.toml` |
| OpenSpec | ETHOS owns governance docs and lifecycle gates around the official OpenSpec workspace. | `docs/governance/openspec-governance.md`, `ethos openspec --lifecycle --json` |
| Quality gates | Owner scripts cover tests, lint, typing/import boundaries, docs/prose/config, security, local state, CI templates, release supply chain, and MCP smoke. | `tools/ci/scripts/*`, `.config/checks/**`, `ethos prove --json` |
| Architecture projection | Architecture docs and generated Mermaid/C4-style projections are communication surfaces, not authority. | `docs/architecture/**`, `.config/checks/architecture/**`, `tools/ci/scripts/run-architecture-projection-drift.sh` |
| Cross-repo references | Adopter mechanisms such as nox, pixi, Pants, Docker/local CI, GitLab local state, MCP, and tooling catalogs belong behind profiles until parity evidence promotes them. | `ethos parity shadow --adopter <profile> --target <repo> --execute --json` |

## Admission Decisions

| Topic | Decision | Rationale | Admission condition |
| --- | --- | --- | --- |
| `nox` | Deferred adapter, not ETHOS core. | ETHOS already has owner scripts and gate registry; nox is useful when an adopter already owns `noxfile.py`, but would duplicate the command plane if made core. | Add only as an adopter/profile bridge with owner script, config path, and proof surface. |
| `pixi` | Deferred environment adapter. | Useful for reproducible conda-like environments in some adopters; ETHOS product runtime is still `uv` unless evidence changes the tool contract. | Add profile checks for adopter lock freshness and host availability; do not replace the product runtime path by analogy. |
| `pants` | Deferred graph/build adapter. | Some adopters need graph/build evidence; ETHOS should not make a build graph engine a truth center before scale or parity evidence requires it. | Admit when package graph scale or adopter parity requires graph evidence beyond owner scripts. |
| `Dagger` | Candidate portable-runner adapter. | It may unify local/hosted CI emulation later, but it is an execution adapter rather than an ontology anchor. | Pilot only after the local emulator evidence model is stable. |
| OpenSpec profile checks | Official-compatible customization. | The extension point must preserve official validation semantics instead of creating an unofficial fork. | Official validation passes first; ETHOS profile/schema checks run afterward and are documented. |
| Superpowers and method packs | Optional method packs. | They can guide process but cannot satisfy ETHOS proof, evidence, or authority. | Use as replaceable workflow aids; never make them required runtime dependencies. |
| C4 / LikeC4-style diagrams | Projection. | Diagrams improve communication, but source truth remains tracked source/docs/system declarations. | Require projection drift checks and generated-artifact boundaries. |

## Work Packages

### P0 — Publication and lane hygiene

Goal: make local state closeable without hiding external lane residue.

Tasks:

- Keep accepted `dev`, `candidate/dev`, and `origin/dev` as separate states.
- Retire only owner-authorized Work Lanes; do not delete foreign or missing-lease
  work without handoff or maintainer break-glass evidence.
- Keep local publish readiness separate from remote push and hosted provider
  observations.

Evidence:

```bash
ethos status --json
ethos lane status --json
ethos report --json
ethos publish --json
```

### P1 — Forge parity and local CI emulation

Goal: make GitHub and GitLab projections over one kernel.

Tasks:

- Keep `.github/workflows/ci.yml` and `.gitlab-ci.yml` generated from or checked
  against shared policy.
- Run GitHub and GitLab local emulators as local evidence only.
- Run hosted provider observation separately and report missing provider access
  as an observation gap, not a proof failure.

Evidence:

```bash
tools/ci/scripts/run-ci-template-check.sh
tools/ci/scripts/run-github-local-emulator.sh
tools/ci/scripts/run-gitlab-local-emulator.sh
tools/ci/scripts/run-hosted-provider-observation.sh
```

### P2 — OpenSpec official-compatible customization

Goal: adapt OpenSpec schema/profile behavior through official extension points
while preserving official validation semantics.

Tasks:

- Document official validation as the first authority.
- Add ETHOS profile checks only after official validation.
- Keep completed OpenSpec changes archived and protected residue blocked.

Evidence:

```bash
ethos openspec --lifecycle --json
ethos audit --mode shape --json
ethos prove --gate openspec --json
```

### P3 — Method-pack and agent boundary

Goal: make repo-local skills, Superpowers, MCP, and other agent tools useful but
replaceable.

Tasks:

- Keep repo-local skills as projections over repository truth.
- Do not vendor external method-pack instructions into ETHOS authority.
- Promote durable learning into tracked rules, docs, schemas, claims, evidence,
  or decisions; never rely on host memory as truth.

Evidence:

```bash
ethos quality claims --json
ethos report --json
ethos assistants doctor --json
```

### P4 — Quality, format, lint, security, and supply chain

Goal: make quality gates owner-scripted, cataloged, and reproducible.

Tasks:

- Keep `system/tools.toml` as tool-adoption state SSOT.
- Preserve owner scripts for tests, lint, import boundaries, markdown, prose,
  config, shell/yaml, security, dependency, coverage, release supply chain,
  local state, and closeout manifests.
- Add new tools only with owner script, config path, artifact path, and proof
  surface.

Evidence:

```bash
tools/ci/scripts/run-python-tests.sh
tools/ci/scripts/run-python-lint.sh
tools/ci/scripts/run-import-linter.sh
tools/ci/scripts/run-markdown-lint.sh
tools/ci/scripts/run-prose-check.sh
tools/ci/scripts/run-config-lint.sh
tools/ci/scripts/run-secrets-scan.sh
tools/ci/scripts/run-release-supply-chain.sh
```

### P5 — Architecture and projection drift

Goal: communicate architecture through diagrams without making diagrams truth.

Tasks:

- Keep architecture authority in tracked source, docs, and system declarations.
- Generate Mermaid/C4-style projections under generated-artifact rules.
- Run architecture projection drift checks before claiming docs-code alignment.

Evidence:

```bash
tools/ci/scripts/run-module-layout.sh
tools/ci/scripts/run-architecture-projection-drift.sh
ethos prove --gate repository-audit --json
```

### P6 — Adopter parity profiles

Goal: verify ETHOS adoption profiles on real repositories.

Tasks:

- Treat heavy-tooling mechanisms such as nox, pixi, Pants, Docker/local CI, and
  rich quality gates as profile evidence until productized.
- Treat tooling-control-plane mechanisms such as pixi, GitLab/local CI, MCP
  catalogs, runtime catalogs, and repo config contracts as profile evidence
  until productized.
- Use parity shadow evidence to decide which mechanisms become ETHOS adapters.

Evidence:

```bash
ethos parity shadow --adopter <profile-id> --target <adopter-root> --execute --write-evidence --json
ethos parity gaps --adopter <profile-id> --target <adopter-root> --json
```

## Sequencing

1. Close local lane/publish hygiene before remote publication.
2. Stabilize forge/local-CI evidence before adding Dagger or new CI engines.
3. Stabilize OpenSpec official-compatible profile checks before extending schema
   assertions.
4. Keep quality gates green before adding new tools.
5. Add architecture projection drift gates before treating generated diagrams as
   review artifacts.
6. Validate adapters against adopter profiles before promoting them to default
   ETHOS behavior.

## Completion Audit

The program is complete for a reviewed HEAD only when all of the following are
true for that HEAD:

- `ethos status --json` has no required gaps for the target checkout.
- `ethos report --json` distinguishes required gaps, hard quality gaps,
  advisory coordination risk, local publication state, and hosted observation
  state.
- `ethos openspec --lifecycle --json` has no completed-but-unarchived residue.
- GitHub and GitLab template checks pass from shared policy.
- Local emulator evidence exists for both forge profiles, or missing optional
  host tools are reported as bounded local gaps.
- `system/tools.toml` records adoption state for active, candidate, deferred,
  and rejected tools.
- Architecture projection drift has been checked.
- Adopter-profile findings are either closed or explicitly recorded as
  adopter-profile gaps.
- Method packs remain replaceable and non-authoritative.
