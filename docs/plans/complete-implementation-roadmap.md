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

Purpose: turn the July 2026 planning discussion into one execution map for
forge parity, local CI emulation, OpenSpec governance, method-pack boundaries,
format/lint/architecture/C4/tooling, and adopter validation against
heavy-tooling and tooling-control-plane adopter profiles.

This roadmap does not replace the narrower
[Tooling Adoption Roadmap](tooling-adoption-roadmap.md),
[Mechanism Comparison Audit](../reference/mechanism-comparison-audit.md),
[Forge Provider Contract](../governance/forge-provider-contract.md), or
[OpenSpec Governance](../governance/openspec-governance.md). It sequences them
into one implementation program and states the evidence required to close each
slice.

## Target State

ETHOS remains a Git-native governed repository kernel. External systems are
adapters, projections, sensors, or execution backends; none of them becomes
repository truth.

The target state is:

1. **One kernel, two forge projections**: GitHub and GitLab are mirror-like
   repository carriers over the same Git truth, branch roles, gates, templates,
   provider observations, and publication boundary.
2. **Local CI emulator as fallback, not hosted truth**: local GitHub/GitLab
   emulators can prove provider-template shape and local reproducibility, but
   they never claim hosted CI success.
3. **Official OpenSpec plus ETHOS profile checks**: OpenSpec official workspace
   and validation remain first; ETHOS adds official-compatible schema/profile
   checks after official validation, not a forked schema dialect.
4. **Method packs are replaceable**: Superpowers and similar skill packages may
   improve human/agent discipline, but ETHOS truth is source, tests, schemas,
   OpenSpec, evidence, claims, and command JSON.
5. **Quality and architecture are generated/evidenced**: format, lint, type,
   tests, security, supply chain, architecture projection, and C4/Mermaid drift
   checks run through owner scripts and `system/tools.toml`.
6. **Adopter parity is empirical**: heavy-tooling and tooling-control-plane adopter profiles
   validate ETHOS profiles by real shadow/parity runs, not by analogy.

## Baseline Facts

| Area | Current ETHOS baseline | Evidence surface |
| --- | --- | --- |
| Forge parity | `.github/workflows/ci.yml`, `.gitlab-ci.yml`, provider templates, hosted observation script, local emulator scripts. | `docs/governance/forge-provider-contract.md`, `tools/ci/scripts/run-*-emulator.sh`, `tools/ci/scripts/run-hosted-provider-observation.sh` |
| Tool catalog | Active and deferred tools are cataloged in `system/tools.toml`, including nox, pixi, pants, Dagger, architecture projection, provider observation, and local CI. | `system/tools.toml` |
| OpenSpec | ETHOS owns OpenSpec governance docs and lifecycle gates; completed changes are archived and protected residue is checked. | `docs/governance/openspec-governance.md`, `ethos openspec --lifecycle --json` |
| Quality gates | Owner scripts cover Python tests, ruff, ty/import-linter style boundaries, markdown/prose/config, security, local state, CI templates, release supply chain, MCP smoke. | `tools/ci/scripts/*`, `.config/checks/**`, `ethos prove --json` |
| Architecture/C4 | Architecture docs and generated Mermaid projection are tracked; LikeC4-like source is an adapter, not source of truth. | `docs/architecture/**`, `.config/checks/architecture/**`, `tools/ci/scripts/run-architecture-projection-drift.sh` |
| Cross-repo references | A heavy-tooling adopter has nox/pixi/pants plus rich quality gates and local CI; a tooling-control-plane adopter has pixi, GitLab/local CI state, MCP/tooling control-plane catalogs. | Adopter roots supplied at runtime for heavy-tooling and tooling-control-plane adopter profiles |

## Decisions

| Topic | Decision | Rationale | Admission condition |
| --- | --- | --- | --- |
| `nox` | Deferred adapter, not ETHOS core. | ETHOS already has owner scripts and gate registry; nox is useful for adopters such as a heavy-tooling adopter but would duplicate the command plane if made core. | Add only as adopter/profile bridge when a repo already owns `noxfile.py`. |
| `pixi` | Deferred environment adapter. | Useful for reproducible conda-like environments in heavy-tooling and tooling-control-plane adopters; ETHOS currently standardizes on `uv` for its own runtime. | Add profile checks for adopter lock freshness and host availability; do not replace ETHOS `uv` path. |
| `pants` | Deferred graph/build adapter. | A heavy-tooling adopter uses Pants; ETHOS does not yet need a build graph engine as a truth center. | Admit when package graph scale or adopter parity requires graph evidence beyond current scripts. |
| `Dagger` | Candidate portable runner adapter. | May unify local/hosted CI emulation later; not an ontology anchor. | Pilot only after local emulator evidence model stabilizes. |
| OpenSpec schema | Official-compatible customization. | The user explicitly wants official customization, not an unofficial fork. | Official validation passes first; ETHOS profile/schema checks run after it and are documented. |
| Superpowers | Optional method pack. | It can teach practices, but cannot satisfy ETHOS proof, evidence, or authority. | Use as replaceable workflow aid only; never make required runtime dependency. |
| C4 | Projection. | C4/LikeC4 improves communication, but source truth remains tracked docs/source/system. | Require projection drift check and generated artifact boundary. |

## Adopter Mechanism Comparison

| Mechanism | ETHOS | Heavy-tooling adopter profile | Tooling-control-plane adopter profile | ETHOS action |
| --- | --- | --- | --- | --- |
| Branch/work lane governance | Explicit branch roles, leases, prewrite, land, publish. | Worktree/candidate discipline and quality closeout practices. | GitLab/dev branch governance and work tracking configs. | Keep ETHOS native lane kernel; use adopters for profile parity. |
| CI and local emulation | GitHub/GitLab templates, local emulator scripts, hosted observation boundary. | Docker/local GitLab CI tooling and portable CI gates. | GitLab/local CI state plus `.gitlab-ci-local` residue boundary. | Productize local emulator result schema and hosted observation separation. |
| Environment | `uv` and owner scripts. | pixi, nox, Pants, Docker quality tooling. | pixi and tooling package catalogs. | Add adapters only when profile-driven; no core switch. |
| Format/lint | ruff, markdownlint, prose, config, yaml/shell gates. | Rich quality gate modules and ratchets. | Tooling repo configs for docs, format selection, package metadata, public API. | Harden `system/tools.toml` as SSOT; keep owner scripts. |
| Architecture | Docs, generated Mermaid/C4 projection, module/import boundaries. | Architecture/package/import contracts and semantic gates. | Module dependency contracts and repo layout catalogs. | Add architecture drift evidence to proof/report surfaces. |
| OpenSpec | Official workspace plus lifecycle/archive gates. | OpenSpec workspace used as governance carrier. | OpenSpec config and capability registry. | Add official-compatible profile customization, not fork. |
| Agent/method packs | Repo-local skills and activation policy; external skills as method packs. | Agentic skills and worktree governance lessons. | MCP/tooling runtime plus automation configs. | Keep method packs replaceable and promote only durable evidence/skills. |

## Work Packages

### P0 — Stabilize publication and lane hygiene

Goal: make the current repository state closeable without hiding external lane
residue.

Tasks:

- Keep `dev`, `candidate/dev`, and remote `origin/dev` as separate states.
- Retire only owner-authorized Work Lanes; do not delete foreign or missing-lease
  work without handoff.
- Keep local publish readiness separate from remote push.

Evidence:

```bash
ethos status --json
ethos lane status --json
ethos report --json
ethos publish --json
```

### P1 — Forge parity and local CI emulator

Goal: make GitHub and GitLab mirror projections over one kernel.

Tasks:

- Keep `.github/workflows/ci.yml` and `.gitlab-ci.yml` generated or checked from
  shared templates.
- Run GitHub and GitLab local emulators as local evidence only.
- Run hosted provider observation separately and report missing provider access as
  observation gap, not proof failure.

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

- Document the official validation step as first authority.
- Add ETHOS profile checks only after official validation.
- Keep completed OpenSpec changes archived and protected residue blocked.

Evidence:

```bash
ethos openspec --lifecycle --json
ethos audit --mode shape --json
ethos prove --gate openspec --json
```

### P3 — Method-pack and agent boundary

Goal: make Superpowers, repo-local skills, MCP, and other agent tools useful but
replaceable.

Tasks:

- Keep repo-local skills as projections over repository truth.
- Do not vendor Superpowers instructions into ETHOS authority.
- Promote durable learning into tracked rules, docs, schemas, claims, or
  evidence; never rely on host memory as truth.

Evidence:

```bash
ethos quality claims --json
ethos quality claims --json
ethos report --json
```

### P4 — Quality, format, lint, security, and supply chain

Goal: make quality gates owner-scripted, cataloged, and reproducible.

Tasks:

- Keep `system/tools.toml` as adoption state SSOT.
- Preserve owner scripts for Python tests, ruff, import boundaries, markdown,
  prose, config, shell/yaml, security, dependency, coverage, release supply chain,
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

### P5 — Architecture and C4 projection

Goal: communicate architecture through diagrams without making diagrams truth.

Tasks:

- Keep architecture source in tracked source/docs/system declarations.
- Generate Mermaid/C4 projections under generated-artifact rules.
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

- Treat the heavy-tooling adopter profile as the heavy-tooling profile: nox, pixi, Pants, Docker/local CI,
  rich quality gates.
- Treat the tooling-control-plane adopter profile as the tooling-control-plane profile: pixi, GitLab/local CI,
  MCP/runtime catalogs, repo config contracts.
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
5. Add architecture/C4 drift gates before treating generated diagrams as useful
   review artifacts.
6. Validate adapters against heavy-tooling and tooling-control-plane adopter profiles before promoting them to default
   ETHOS behavior.

## Completion Audit

The program is complete only when all of the following are true on the current
HEAD:

- `ethos status --json` has no required gaps for the target checkout.
- `ethos report --json` distinguishes required gaps, hard quality gaps,
  advisory coordination risk, and local/hosted publication state.
- `ethos openspec --lifecycle --json` has no active completed-but-unarchived
  residue.
- GitHub and GitLab template checks pass from shared policy.
- Local emulator evidence exists for both provider profiles, or missing optional
  host tools are reported as bounded local gaps.
- `system/tools.toml` records adoption state for active, candidate, deferred,
  and rejected tools.
- Architecture projection drift is checked.
- Heavy-tooling and tooling-control-plane adopter-profile findings are either closed or explicitly recorded as
  adopter-profile gaps.
- Superpowers and other method packs remain replaceable and non-authoritative.
