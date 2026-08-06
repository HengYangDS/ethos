---
subject: ethos:mechanism-comparison-audit
role: reference
state: active
relations:
  canonical_for: reusable mechanism-family assessment behind tooling adoption
  derives_from: docs/plans/tooling-adoption-roadmap.md, docs/governance/product-design-contract.md
---

# Mechanism Comparison Audit

Status: active.

Purpose: preserve the mechanism-family judgment behind the tooling adoption
roadmap without turning any named external repository, adopter, personal work
history, or helper command plane into ETHOS product truth.

See also: [Tooling Adoption Roadmap](../plans/tooling-adoption-roadmap.md),
[Forge Provider Contract](../governance/forge-provider-contract.md),
[Product Design Contract](../governance/product-design-contract.md), and
[Runbook Registry](runbook-registry.md).

## Snapshot Boundary

This audit is a classified mechanism assessment. It may be informed by local
repository observations, user instruction, prior evidence, and product design
review, but the durable product value is the mechanism classification below.

The active reference intentionally does not name external or private source
repositories. Historical evidence and archived OpenSpec records may preserve
facts about specific sources; active product references must stay reusable for
multi-contributor enterprise adopters.

## Verdicts By Mechanism Family

| Mechanism family | Common external pattern | ETHOS product stance | ETHOS action |
| --- | --- | --- | --- |
| Git lifecycle and closeout | Accepted root, candidate train, work lanes, proposal/review boundaries, closeout commands, delivery evidence. | `status -> plan -> prove -> land -> publish`, Work Lanes, candidate train, accepted-root closeout, lane leases. | Keep the ETHOS kernel. Map adopter branch names through profiles only. |
| Command runner and environment | Environment managers, matrix runners, graph tools, and recipe files provide operator convenience. | uv workspace, Hatchling packages, `ethos ...`, and owner scripts under `tools/ci/scripts/`. | Keep one command plane. Admit runners only as adapters. |
| Hosted CI providers | Multiple hosted providers use checked templates and local syntax validation. | GitHub/GitLab templates, tracked projections, CI drift gate, actionlint, local emulator wrappers. | Keep provider mirror semantics; never claim hosted status from local emulators. |
| Local CI emulation | Local provider emulators support dry-run, run, doctor, and handoff evidence. | GitHub and GitLab emulator wrappers plus local-CI owner bundle. | Adopt the minimum emulator contract; deepen handoff and hosted observation later. |
| Format policy | Tool-native formatters and format-selection policy route file types to owners. | `.config/checks/format/selection.toml` plus `uv run --frozen --offline python -m nox -s format_selection`. | Fail closed for unregistered executable carriers and narrow carrier homes; add fix modes only after stable ownership. |
| Python lint, type, and test | Broad lint, type, test, import, property, performance, mutation, and report matrices. | Ruff, ty, pytest/coverage, import-linter, docstring coverage, module layout, repository hygiene. | Keep compact hard floor; add matrix breadth only for ETHOS product risk. |
| Docs, prose, and config lint | Markdown/prose/config hygiene, documentation metadata, and generated report checks. | Markdownlint, Taplo, Yamllint, JSON syntax, docs registry/topology, shell lint. | Prose and metadata breadth remain maturity debt until owner config, runner, CI projection, and proof exist. |
| Security and dependency hygiene | Secret scanning, dependency audits, vulnerability scans, tool-supply governance. | Gitleaks, Ruff security rules, dependency hygiene, native `uv audit` over `uv.lock`, schema hygiene, prose spelling, SBOM, and release attestation active; image scanning remains planned. | Keep one native lock audit owner and activate image scanners only through pinned tool supply and owner surfaces. |
| Architecture and diagrams | Import boundaries, package topology, dependency graphs, C4-like model projections. | Import-linter, module-layout, source-owned C4-like model, Mermaid projection, architecture drift gate. | Keep lightweight source-to-projection gate; richer diagram stacks remain optional. |
| OpenSpec carriers | Official OpenSpec plus accepted specs, active deltas, Commitment, and evidence refs. | Official `doctor`, `list`, `status`, strict validation, and owner-native archive; ETHOS observes the active self-profile carrier without predicting archive or re-evaluating history. | Use compatible extension; do not fork OpenSpec syntax, archive behavior, or `WHEN`/`THEN` semantics. |
| Evidence and history | Delivery evidence, closeout logs, retained manifests, and cleanup observations. | Attestations are durable evidence; Chronicle, parity, reports, and indexes are derived historical projections. | Keep evidence kinds explicit without restoring parallel truth stores. |
| Local and generated state | Generated-state grammar, cache routing, local-state audit/clean, reproducible runtime hygiene. | Build/evidence/runtime boundaries and local-state audit gate. | ETHOS has the invariant; add cleanup apply modes separately. |
| Runbook and operator UX | Recipe files and generated runbook views expose local CI, worktree, proof, OpenSpec, and closeout commands. | `docs/reference/runbook-registry.md` plus drift checks. | Derive future views from Cyclopts/API operations and gate declarations, not manual command tables. |
| MCP and agent projections | MCP readiness, assembly catalogs, materialized overlays, host probes, and assistant directives. | Agent projection docs, Skills V2, MCP smoke gate. | Keep MCP replaceable and read-mostly; do not make MCP semantic center. |
| Agent method packs | External planning/review/verification disciplines guide agent work. | Adapter-only method-pack entries; no runtime/package dependency. | Optional and replaceable. ETHOS needs equivalent evidence discipline, not a specific pack. |
| Task ledger and intake | Task ledgers can integrate boards, lanes, statements, and closeout. | Self-profile OpenSpec tasks plus optional task-ledger adapters. | Keep task UI adapter-only; Commitment and Attestation semantics stay ETHOS-owned. |
| Release and supply chain | Package smoke, reproducibility, SBOM, signing, artifact policy, provider release observation. | Syft SPDX 2.3 JSON over the exact built wheel; local receipt binds artifact/SBOM digests and tool version. | Provenance, signing, upload, and image scanning require distinct provider receipts. |
| Domain runtime | Domain-specific data, cache, SQL, orchestration, compatibility, and observability mechanics. | Repository governance product only. | Do not absorb domain runtime. Govern it as adopter subject through profiles. |

## What ETHOS Has More Of

ETHOS is strongest where repository mutation must be legible and enforceable:

1. one explicit kernel chain and transition loop instead of a broad helper-command
   surface;
1. Work Lane admission, accepted-root protection, candidate closeout, and
   evidence-bound publication separation as product semantics;
1. OpenSpec as governance carrier plus ETHOS lifecycle checks, without making
   OpenSpec a second command plane;
1. provider projections over owner scripts instead of provider-specific policy
   duplication;
1. schema-bound command JSON, invalid-state reduction, and proof/report/publish
   separation;
1. adapter taxonomy for provider, environment, task, agent, architecture,
   release, and adopter-domain mechanisms.

## What ETHOS Has Less Of

ETHOS is deliberately or temporarily lighter in these areas:

1. no universal environment-runner matrix in the product runtime;
1. no task-ledger product dependency in the product runtime;
1. less full-stack local CI emulator handoff and runtime matrix breadth;
1. less prose/metadata breadth until owner surfaces exist;
1. less multi-scanner vulnerability breadth until OSV and image/package scanners
   are admitted through pinned tool supply and owner surfaces;
1. less MCP assembly/runtime breadth by design;
1. no domain runtime mechanics in the product runtime;
1. no external signing upload, hosted CI observation capture, image scan, or
   release publication adapter as current truth.

## Adoption Rules

Use these rules when judging future tooling proposals:

1. A mechanism enters ETHOS only as one of: kernel contract, adapter, evidence
   class, projection, or quality gate.
1. A tool becomes an active gate only after it has a `system/tools.toml` entry,
   owner config, reusable runner or `ethos ...` surface, provider/hook
   projection, and proof coverage.
1. Local emulators produce local evidence only; hosted success requires hosted
   provider facts.
1. Agent method packs, MCP, task ledgers, environment runners, graph tools,
   hosted providers, container runners, and release/signing tools remain
   replaceable unless a future accepted decision explicitly changes their
   binding class.
1. Domain runtime mechanisms remain adopter truths; ETHOS may govern them as
   subjects, but does not become them.
1. Active product references must not require knowledge of a named private
   repository, personal work history, or single author to understand the product.

## Completion Closeout

The July 9 closeout binds the mechanism audit to the repository's completed
current baseline. ETHOS has accepted the mechanism value from the compared
repositories where it reduces invalid states for a broad governed-repository
audience, and it has rejected ontology drift where a mechanism belongs to an
adopter, provider, host, method pack, or local operator workflow.

Completed current baseline:

1. GitHub and GitLab are symmetric provider projections over one ETHOS command
   and evidence contract.
1. Local CI fallback, GitHub emulator, GitLab emulator, and hosted-provider
   observation are separate evidence classes with hosted success unclaimed by
   local evidence.
1. OpenSpec remains the official native carrier selected by the ETHOS self
   profile; generic adopters need not install it. ETHOS adds Commitment and
   active-scope observations without duplicating official archive behavior.
1. Format selection, lint, dependency hygiene, JSON Schema hygiene, prose
   spelling, Python vulnerability audit over uv-exported resolved requirements,
   architecture/C4 projection drift, runbook, MCP smoke, local-state, closeout
   manifest, SBOM, and release-attestation gates have active owner surfaces
   where cataloged as active.
1. Nox, Pixi, Pants, task ledgers, Dagger, Superpowers, OSV, image/package
   scanning, external signing, and richer hosted artifact capture remain
   adapter/profile sequencing unless separately promoted by evidence.

The closeout is locally proven only. It does not claim hosted CI success, remote
publication, remote release, or adopter-domain runtime parity.

## Current Conclusion

The current ETHOS form is suitable for selective adoption, not wholesale tool
import. The right path is to strengthen the evidence and projection surface while
preserving the small product kernel:

```text
absorb mechanism value;
reject adopter ontology drift;
prove active gates before calling them current.
```
