---
subject: ethos:tooling-adoption-roadmap
role: plan
state: planned
relations:
  canonical_for: planned adoption of dmgr and di-effect mechanisms
  derives_from: dmgr and di-effect repository comparison, ETHOS product design contract
---

# Tooling Adoption Roadmap

Status: planned.

Purpose: turn the dmgr and di-effect mechanism comparison into a sequenced
ETHOS adoption plan without copying adopter tooling into product ontology.

This is a plan, not current runtime truth. A roadmap item becomes current only
after the corresponding source, tests, schema, OpenSpec, claim, evidence, and
command output land through the ETHOS lifecycle.

## Planning Axiom

ETHOS should absorb mature mechanisms as contracts, profiles, adapters,
projections, or gates. It should not promote adopter tools into ontology anchors.

```text
mechanism value -> ETHOS contract/profile/adapter/gate/projection
not
adopter tool -> ETHOS core dependency
```

The public loop remains:

```text
status -> plan -> prove -> land -> publish
```

## Current Baseline

ETHOS already has:

- a Git-native governed repository model;
- branch roles and Work Lane lifecycle;
- claim/evidence/chronicle records;
- mandatory official OpenSpec governance plus ETHOS lifecycle checks;
- schema-governed command JSON;
- compact owner-script quality gates under `tools/ci/scripts/`;
- a tool catalog in `system/tools.toml` that distinguishes active and planned
  tools.

The comparison with dmgr and di-effect shows gaps in provider parity, local
provider emulation, architecture projection, broader quality gates, closeout
operations, and runbook discoverability.

## Horizontal Mechanism Matrix

This matrix compares mechanisms observed in the dmgr reference repository,
the di-effect reference repository, and the current ETHOS Work Lane. It compares
mechanism value, not authority: an adopter mechanism may be mature without
becoming ETHOS ontology.

| Mechanism family | dmgr | di-effect | ETHOS current lane | ETHOS delta and verdict |
| --- | --- | --- | --- | --- |
| Repository lifecycle | `dev` accepted root, `candidate/dev`, `work/*`, submit/review boundary, closeout commands, Backlog-aware claims. | `dev` coordination root, local `task/*` and `integration/*`, `submit/*` for remote review, closeout/export commands. | `status -> plan -> prove -> land -> publish`, `work/*`, `candidate/dev`, accepted-root closeout, Work Lane admission. | ETHOS is already stronger as product kernel. Do not copy branch names from adopters; map them through profile adapters when adopting. |
| Command and environment authority | Pixi is the public command plane; Nox owns large quality fan-out; uv lock and package metadata remain package substrate; just exposes operator recipes. | Pixi is selected host environment authority; Docker gate wraps runtime checks; `di-effect ...` is the product CLI; just exposes operator recipes. | uv-driven product command plane plus reusable `tools/ci/scripts/*`; `system/tools.toml` records tool identity, profile, owner, and boundary. | ETHOS is intentionally smaller. Pixi/Nox/Just are useful adapters, not required product substrate. |
| Hosted CI providers | GitLab projection is active; local GitLab emulation is mature; GitHub is not a first-class mirror. | GitHub Actions and GitLab CI both exist as tracked hosted projections with consistency policy. | GitHub and GitLab hosted templates and projections are present; template drift check is active. | ETHOS should keep GitHub/GitLab symmetric mirror semantics. Hosted observations remain separate from local proof. |
| Local CI emulation | Docker-first `gitlab-ci-local` gate with doctor/list/dry-run/run/handoff and boundary-labeled evidence. | Local provider emulators cover GitHub `act` and GitLab paths; Docker gate supplies reproducible execution. | `run-github-local-emulator.sh`, `run-gitlab-local-emulator.sh`, local emulator configs, and local-CI owner bundle are active. | ETHOS has the minimum provider-emulator contract. Later lanes should add stronger matrix handoff and hosted trace observation, not conflate emulator proof with hosted status. |
| CI template consistency | CI projection manifest and local GitLab emulator protect GitLab shape. | `.config/tooling/repo/ci_template_consistency.toml` checks GitHub/GitLab projection consistency. | `.config/checks/ci/templates.toml` plus `run-ci-template-check.sh` checks projection drift. | Adopted as ETHOS provider gate. |
| Format policy | Ruff for Python, markdownlint/Prettier wrapper, Taplo, Yamllint, SQLFluff; format surfaces are routed through Nox/Pixi. | Explicit format-selection guide and policy; TOML human-authored default, JSON generated/machine, YAML tool-bound, JSONL evidence streams. | `.config/checks/format/selection.toml` and `run-format-selection.sh` are active. | Adopted as report-first policy. Future tightening should add fix modes only after policy gates stabilize. |
| Python lint/format/type/test | Ruff, ty, pytest, coverage, import-linter, property/perf/mutation/report sessions under Nox. | Ruff, mypy, ty, pytest, coverage, docformatter/pydoclint, changed-scope and matrix tests. | Ruff, ty, pytest/coverage, import-linter, docstring coverage, module layout, and repository hygiene are active. | ETHOS should keep compact hard floor. Add matrix/perf/mutation only when they protect ETHOS product risk rather than copying adopter breadth. |
| Prose/docs/config lint | Markdown, Vale/codespell, Taplo, Yamllint, JSON hygiene, docs contract gates. | Markdownlint, mdformat, Vale, codespell, Taplo, Yamllint, Spectral-like YAML policy, DocOS metadata. | Markdownlint, Taplo/Yamllint/JSON config lint, shell lint, docs registry/topology are active; prose tools are planned. | ETHOS still lacks mature prose/DocOS breadth. Add Vale/codespell as product gates only with config owner, script owner, CI projection, and proof coverage. |
| Security and dependency hygiene | Gitleaks active; dependency audit/deptry; optional Bandit, pip-audit, osv-scanner candidates; package reproducibility gates. | Gitleaks, Bandit, deptry, pip-audit policy, cache/tool supply governance, requirements projections. | Bandit, gitleaks, SBOM, and release attestation are active; deptry, pip-audit, osv-scanner, grype are planned. | ETHOS has baseline security but lacks dependency/vulnerability maturity. Activate through separate security lanes. |
| Architecture boundaries | Import boundaries, package topology, Pants affected/graph launcher, semantic-owner and redundancy audits. | Module dependency contracts, architecture graphs, LikeC4/C4 tool stack, generated diagrams, provider-boundary specs. | Import-linter, module-layout, C4-like source under `.config/checks/architecture/`, Mermaid projection, and drift gate are active. | ETHOS adopted the projection pattern, not the full LikeC4 stack. Full LikeC4 remains optional until it proves value over the lightweight owner/projection gate. |
| OpenSpec lifecycle and schema/profile | Official OpenSpec workspace plus repo-local SDD lifecycle, Superpowers planning, and claim/evidence promotion. | Official OpenSpec workflow plus repo-local schemas, facets, capability profiles, and provider-boundary specs. | Official validation remains first; ETHOS lifecycle checks add capability profiles, claim binding, evidence refs, and archive closeout. | ETHOS should use official-supported customization and repo-local schemas after official validation. Do not fork `WHEN`/`THEN` semantics or invent a private OpenSpec replacement. |
| Claims, evidence, and chronicle | Rich delivery evidence, parity evidence, closeout logs, local handoff, retained evidence manifests, evidence pruning. | `var/` artifact taxonomy, generated metadata, runbook registry, docs metadata, policy reports, evidence bundles. | Claims, chronicle, parity ledger, closeout evidence manifest, local-state audit, and proof evidence exist. | ETHOS has the kernel and selected P1 evidence operations. It still lacks retained evidence digest, prune/apply cleanup, and hosted trace observation. |
| Local state and generated artifacts | Detailed generated-state grammar, local state audit/clean, build evidence roots, Docker gate hygiene. | `var/` canonical runtime layout, `sitecustomize.py` pycache routing, generated docs metadata, cache policy. | Generated artifact topology, build/evidence boundary, local-state audit gate. | ETHOS has the invariant; dmgr/di-effect have more operational breadth. Add cleanup and fixed-point apply modes later. |
| Runbook and operator UX | Just recipes and docs expose local CI, worktree, proof, Backlog, OpenSpec, and closeout commands. | Large justfile, `di-effect ...` runbooks, generated runbook registry, docs onboarding. | `docs/reference/runbook-registry.md` and `run-runbook-registry-check.sh` are active. | Adopted minimum registry. Future work should generate from command registry instead of manual tables. |
| MCP and agent projections | MCP/ACP readiness and official plugin boundaries appear as planning and host-readiness evidence. | MCP catalog/assembly/materialized overlays, optional GitHub/GitLab/MCP servers, skills and agent directives. | Agent projection docs, repo-local Skills V2, MCP manifest surfaces, and local MCP smoke are active. | ETHOS has projection smoke but not di-effect's full MCP assembly. Keep MCP replaceable and read-only by default. |
| Superpowers | Official plugin is a development workflow boundary, not package runtime; Superpowers artifacts are not truth until promoted. | Superpowers appears as external analogue/harness vocabulary, not kernel dependency. | Superpowers-compatible method pack is planned adapter-only; no vendored runtime dependency. | Superpowers is replaceable. ETHOS needs the discipline contract, not the plugin as substrate. |
| Task ledger and intake | Backlog.md is integrated with tasks, boards, claims, Work Lanes, and closeout readiness. | Task branches and autonomy/directive control plane exist; Backlog is not the kernel. | ETHOS intake/campaign concepts exist; Backlog-compatible task ledger remains adapter-only planned. | Do not make Backlog core. A task UI may project work, but Change/Claim lifecycle stays ETHOS-owned. |
| Release and supply chain | Package smoke, deploy smoke, package manifest, reproducibility, release sessions, GitLab release guidance. | Release docs, package/build policy, cache/tool supply, vulnerability and artifact policy. | SBOM, release attestation, release policy envelope, local release supply-chain gate are active. | ETHOS has native local release evidence. External signing, image scan, and vulnerability adapters remain separate lanes. |
| Domain-specific runtime mechanisms | Raw/cache parity, NIO cache, SQL/DolphinDB/getraw, DQC, alphasim compatibility. | Dependency injection, data-platform, orchestration, observability, MCP/data tools. | Repository governance product, not a data/runtime framework. | Do not absorb domain mechanisms. Mine evidence, parity, and adapter patterns only. |

## Net Difference

Compared with dmgr, ETHOS is now stronger in product-kernel clarity,
GitHub/GitLab mirror design, official-compatible OpenSpec lifecycle checks, and
schema-bound command JSON. ETHOS is still lighter than dmgr in Pixi/Nox matrix
operation, package reproducibility, GitLab-local handoff depth, Backlog
integration, retained evidence/prune operations, and domain-specific parity
gates.

Compared with di-effect, ETHOS is now tighter in bounded land/publish
governance, evidence/claim promotion boundaries, and compact product-loop
semantics. ETHOS is still lighter than di-effect in Docker-first runtime
automation, full dual-provider CI breadth, generated DocOS metadata, MCP
assembly, LikeC4/tool-stack registry, broad `policy run` coverage, and
cross-platform matrix breadth.

Therefore the adoption posture is selective convergence:

1. promote mechanisms that reduce invalid states into ETHOS gates or evidence
   classes;
1. keep provider, environment, task, agent, architecture, and release tools as
   replaceable adapters;
1. reject domain-specific runtime mechanisms unless they are being governed as
   adopters;
1. never let a helper command plane replace `status -> plan -> prove -> land ->
   publish`.

## Adoption Ledger

| Mechanism | Source lesson | ETHOS adoption form | Priority | Core? |
| --- | --- | --- | --- | --- |
| GitHub/GitLab mirror CI | di-effect dual hosted templates | Forge provider contract, templates, drift gate | P0 | Provider projection |
| GitLab local emulator | dmgr boundary-labeled `gitlab-ci-local` | `local_gitlab_emulator` evidence class | P0 | Adapter |
| GitHub local emulator | di-effect `act` wrapper | `local_github_emulator` evidence class | P0 | Adapter |
| Template consistency | di-effect `ci_template_consistency.toml` | `ethos ci templates check` / quality gate | P0 | Gate |
| `actionlint` | di-effect GitHub workflow validation | Provider syntax gate | P0 | Tool gate |
| OpenSpec custom schema/profile | ETHOS existing capability profiles | Official-compatible ETHOS profile validation | P0 | Governance dependency extension |
| Superpowers discipline | dmgr official plugin boundary | Optional method-pack adapter; no vendoring | P0 | No |
| LikeC4 / C4 | di-effect accepted LikeC4 decision | Architecture projection emitting Mermaid | P1 | Projection |
| Format-selection policy | di-effect format policy | Report-first format policy audit | P1 | Gate/profile |
| Dependency hygiene | di-effect deptry; dmgr dependency audit | `deptry` planned product gate | P1 | Tool gate |
| Vulnerability scan | di-effect pip-audit | `pip-audit` / `osv-scanner` security profile | P1 | Tool gate |
| Closeout doctor | dmgr closeout review summary | ETHOS closeout evidence manifest/check | P1 | Evidence operation |
| Local-state audit/clean | dmgr generated-state grammar | ETHOS local-state audit/clean gate | P1 | Evidence operation |
| Runbook registry | di-effect runbook registry | Generated command/runbook registry | P2 | Documentation projection |
| MCP smoke | di-effect MCP smoke | Agent projection smoke gate | P2 | Adapter gate |
| SBOM/signing/attestation | ETHOS standards roadmap | Release profile gates | P2 | Release adapter |
| Nox | dmgr nox matrix | Python adopter runner adapter only | Optional | No |
| Pixi | dmgr portable command plane | Environment/toolchain adapter only | Optional | No |
| Pants | dmgr graph smoke | Changed-scope/graph adapter only after need | Optional | No |
| Backlog | dmgr task ledger | Optional task/intake adapter | Optional | No |
| `di-effect policy run` | di-effect large policy command | Mine checks; do not copy command plane | No direct adoption | No |

## P0 Work Package: Provider Parity And Local Emulation

Deliverables:

1. Add provider-neutral CI contract and docs.
1. Add hosted templates for GitHub Actions and GitLab CI under `.config/ci/templates/hosted/`.
1. Make tracked hosted files generated-or-checked projections.
1. Add template drift check and generated-file presence policy.
1. Add `actionlint` for GitHub workflow syntax.
1. Add local provider emulator entrypoints:
   - GitHub: `act` wrapper;
   - GitLab: `gitlab-ci-local` wrapper.
1. Emit evidence with `hosted_github_status_claimed=false` and
   `hosted_gitlab_status_claimed=false` for emulator runs.
1. Keep local owner gate, local emulator, hosted observation, and remote
   publication as separate evidence classes.

Acceptance evidence:

- `ethos quality tool-profiles --json` shows provider tools with correct
  profiles and planned/active states.
- provider template drift check fails on deliberate drift;
- local emulator wrappers refuse trust-bearing runs with untracked materialized
  inputs unless explicitly allowed for non-proof modes;
- `ethos publish --json` distinguishes local proof from hosted observations.

## P0 Work Package: OpenSpec Schema/Profile Customization

ETHOS should customize OpenSpec through official-compatible extension, not by
forking OpenSpec semantics.

Rules:

1. Run official OpenSpec validation first.
1. Add ETHOS validation after official validation.
1. Keep ETHOS-specific profile records in repo-local schemas such as
   `capability-profile.schema.json`.
1. Validate capability profiles, family ownership, proposal facets, claim
   binding, evidence refs, and archive closeout.
1. Never replace official `WHEN` / `THEN` / `AND` semantics with private syntax.

Acceptance evidence:

- `openspec validate --all --strict --json` passes;
- `ethos openspec --lifecycle --json` proves official validation plus ETHOS
  carrier checks;
- active changes without claim binding remain gaps.

## P0 Work Package: Superpowers Boundary

Superpowers is useful agent execution discipline. It is not required ETHOS
substrate.

ETHOS MUST NOT:

- vendor Superpowers skill bodies;
- depend on Superpowers as package runtime;
- make Superpowers a precondition for repository governance;
- treat Superpowers artifacts as proof without promotion into ETHOS evidence.

ETHOS MAY:

- recognize an installed official plugin as an optional method pack;
- record whether a method pack was used for a plan or review;
- map the same discipline to ETHOS-native plan/proof/verification gates;
- allow alternative method packs that satisfy the same evidence contract.

Acceptance evidence:

- agent/skill docs describe Superpowers as replaceable;
- no runtime dependency or vendored copy appears in package metadata;
- method-pack usage never satisfies claim proof by itself.

## P1 Work Package: Quality, Format, Architecture, And C4

Quality additions should extend the current hard floor without producing a
second quality authority.

Deliverables:

1. Activate `deptry` after config owner, script owner, CI projection, and proof
   coverage exist.
1. Activate `pip-audit` and `osv-scanner` under security profile.
1. Add report-first `format_selection` audit for Python, Markdown, TOML, YAML,
   JSON, shell, and ecosystem-native formats.
1. Add C4/LikeC4 model owner and export-to-Mermaid projection.
1. Add architecture projection drift check so generated diagrams cannot become
   unreviewed truth.
1. Add semantic-owner/redundancy audits only when they produce actionable,
   bounded findings.

Acceptance evidence:

- every active tool has `system/tools.toml`, config owner, reusable gate, CI/hook
  projection, and proof coverage;
- LikeC4 artifacts are projections and can be regenerated from tracked source;
- no generated diagram overrides source/docs/OpenSpec truth.

## P1 Work Package: Evidence Operations

ETHOS should absorb dmgr's practical evidence operations:

- closeout evidence manifest;
- retained evidence digest manifest;
- local-state audit and cleanup plan;
- hosted CI trace scan as observation, not hosted truth;
- local handoff summary that cites local proof and explicitly names missing
  hosted evidence.

Acceptance evidence:

- closeout summaries hash referenced artifacts;
- cleanup plans are plan-first and fixed-point checked in apply mode;
- hosted trace scans are labeled observations and cannot claim provider success
  without provider status facts.

## P2 Work Package: Runbook, MCP, Release Supply Chain

Deliverables:

1. Generate a runbook registry from command registry, docs, and tests.
1. Add MCP projection smoke for configured agent adapters.
1. Add SBOM/signing/attestation gates under release profile.
1. Add provider artifact observation capture for GitHub and GitLab.

Deferred non-goals for this change: external signing upload, image/package scanning, and vulnerability-adapter activation remain separate Work Lanes until tool supply, owner configs, runner scripts, CI projections, and proof coverage exist.

Acceptance evidence:

- runbook registry drift is checked;
- MCP smoke logs are evidence artifacts, not truth stores;
- release profile can emit SBOM/provenance/signature evidence without requiring
  adopters to use the same release substrate.

## Non-Adoption Decisions

| Tool | Decision | Reason |
| --- | --- | --- |
| Nox | Optional Python profile adapter | Duplicates ETHOS owner-script/proof command plane if made core. |
| Pixi | Optional environment adapter | Useful for dmgr portability, too strong as universal ETHOS runtime. |
| Pants | Optional graph/changed-scope adapter | No proven core-scale graph need yet. |
| Backlog | Optional task/intake adapter | Task UI must not own Change/Claim lifecycle. |
| Superpowers | Optional method-pack adapter | Replaceable agent discipline, not repository truth. |
| `di-effect policy run` | Mine for checks only | Would create a parallel command plane. |

## Sequencing Rule

A planned tool becomes an active ETHOS gate only when all five owner surfaces
exist:

1. `system/tools.toml` explains why/profile/boundary;
1. config owner exists under `.config/checks/` or a native owner;
1. reusable execution surface exists under `tools/ci/scripts/` or `ethos ...`;
1. hosted CI/hooks invoke the owner surface without duplicating policy;
1. tests/proof assert the contract.

Until then it remains planned and MUST NOT be reported as an active quality
floor.
