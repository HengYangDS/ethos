---
subject: ethos:tooling-adoption-roadmap
role: plan
state: active
relations:
  canonical_for: completed baseline and future sequencing for reusable product tooling mechanisms
  derives_from: ETHOS product design contract, system tool catalog, quality gate policy
---

# Tooling Adoption Roadmap

Status: active baseline plus future sequencing.

Purpose: define how ETHOS admits reusable tooling mechanisms without turning
any adopter repository, personal work history, hosted provider, or helper tool
into product ontology.

See also: [Forge Provider Contract](../governance/forge-provider-contract.md),
[Mechanism Comparison Audit](../reference/mechanism-comparison-audit.md),
[OpenSpec Governance](../governance/openspec-governance.md), and
[Runbook Registry](../reference/runbook-registry.md).

This document now separates the completed current baseline from future adapter
sequencing. A mechanism is current only when source, tests, schema or
configuration owner, OpenSpec carrier, claim, evidence, and command output have
landed through the ETHOS lifecycle. A mechanism listed as planned, optional, or
deferred remains future work even when its design appears here.

## Completion Boundary

The July 9 planning and execution closeout completed the repository-truth
baseline for the requested tooling plan. Current truth is limited to the owner
surfaces, gates, specs, claims, and evidence that have landed in this repository.
Future sequencing remains explicit so ETHOS does not confuse a roadmap entry
with an active gate.

Completed baseline:

- GitHub and GitLab are symmetric forge-provider projections over one
  Git-native ETHOS contract.
- Provider templates, tracked hosted CI files, and template drift checks are
  active owner surfaces.
- Local GitHub and GitLab emulator wrappers emit local evidence only and set
  hosted-status claim booleans to false.
- The local CI fallback bundle is HEAD-stable local owner-gate evidence, not
  hosted CI proof.
- OpenSpec remains a mandatory official governance dependency, with
  official-compatible ETHOS capability/profile, claim-binding, evidence-ref, and
  archive lifecycle checks layered after official validation.
- Format selection, dependency hygiene, prose spelling, JSON Schema hygiene,
  Python vulnerability audit over uv-exported resolved requirements, C4-like
  architecture projection drift, runbook registry, MCP smoke, closeout evidence
  manifest, local-state audit, hosted-provider observation, SBOM, and release
  attestation envelopes have active owner surfaces where cataloged as active.
- Superpowers, Nox, Pixi, Pants, task ledgers, Dagger, external signing, OSV,
  image/package scanning, and broad policy suites remain adapter/profile work
  unless a later accepted decision and proof promote a specific bounded gate.

Non-claims:

- No hosted GitHub status is claimed by local gates or local emulators.
- No hosted GitLab status is claimed by local gates or local emulators.
- No remote publication or remote release is claimed by the local closeout.
- No domain runtime from an adopter repository becomes ETHOS product ontology.
- No method pack, MCP server, environment runner, or graph build system becomes
  required ETHOS substrate.

## Adoption Axiom

ETHOS absorbs mechanisms as contracts, profiles, adapters, projections, or
gates. It does not absorb adopter-specific domains, private repository names,
operator habits, or a second command plane.

```text
mechanism value -> ETHOS form -> owner surface -> proof -> active gate
```

A candidate mechanism is admissible only when it reduces invalid states for a
broad enterprise repository audience and can be governed by the same
`status -> plan -> prove -> land -> publish` loop.

## Current Product Baseline

ETHOS already has these product-native mechanisms:

- one governed Git repository model;
- branch roles and Work Lane lifecycle;
- claim, evidence, and chronicle records;
- mandatory OpenSpec governance plus ETHOS lifecycle checks;
- schema-governed command JSON;
- compact owner-script quality gates under `tools/ci/scripts/`;
- a tool catalog in `system/tools.toml` that distinguishes active and planned
  tools;
- product-boundary and contributor-policy gates that keep distribution and
  identity organization-native.

## Mechanism Families

| Mechanism family | ETHOS adoption form | Priority | Core? |
| --- | --- | --- | --- |
| Hosted CI provider parity | Provider contract, hosted templates, template drift gate | P0 | Provider projection |
| Local CI emulation | Local emulator wrappers with evidence-bound trust labels | P0 | Adapter |
| Template consistency | `ethos` quality gate over tracked provider projections | P0 | Gate |
| OpenSpec profile customization | Official validation first, then ETHOS lifecycle/profile checks | P0 | Governance extension |
| Agent method packs | Optional method-pack adapter; no runtime dependency | P0 | No |
| Format-selection policy | Report-first file-format boundary audit | P1 | Gate/profile |
| Dependency hygiene | Tool-specific profile after config owner and proof coverage exist | P1 | Tool gate |
| Vulnerability scanning | Security profile gates with separate tool supply governance | P1 | Tool gate |
| Closeout evidence operations | Evidence manifest, retained digest, local-state cleanup plan | P1 | Evidence operation |
| Architecture projection | Source-owned model with generated diagram drift checks | P1 | Projection |
| Runbook registry | Generated command/runbook registry with drift check | P2 | Documentation projection |
| MCP smoke | Agent projection smoke gate; logs are evidence, not truth stores | P2 | Adapter gate |
| SBOM/signing/attestation | Release profile gates and provenance envelopes | P2 | Release adapter |
| Environment runners | Optional adapter only when adopter profile needs them | Optional | No |
| Task ledgers | Optional task/intake adapter; Change/Claim lifecycle stays ETHOS-owned | Optional | No |
| Broad policy suites | Mine checks; do not copy command planes | Optional | No |

## P0 Work Package: Provider Parity And Local Emulation

Deliverables:

1. Keep provider-neutral CI contract and docs as the authority.
1. Keep hosted templates for GitHub Actions and GitLab CI under tracked
   projection owners.
1. Make tracked hosted files generated-or-checked projections.
1. Keep template drift checks and generated-file presence policy active.
1. Add provider syntax gates only when the tool has an owner config and script.
1. Keep local provider emulator entrypoints separate from hosted observations.
1. Emit evidence with hosted-provider success explicitly unclaimed for emulator
   runs.
1. Keep local owner gate, local emulator, hosted observation, and remote
   publication as separate evidence classes.

Acceptance evidence:

- `ethos quality tool-profiles --json` shows provider tools with correct
  profiles and planned or active states;
- provider template drift check fails on deliberate drift;
- local emulator wrappers refuse trust-bearing runs with untracked materialized
  inputs unless explicitly allowed for non-proof modes;
- `ethos publish --json` distinguishes local proof from hosted observations.

## P0 Work Package: OpenSpec Schema/Profile Customization

ETHOS customizes OpenSpec through official-compatible extension, not by forking
OpenSpec semantics.

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

## P0 Work Package: Agent Method-Pack Boundary

Agent method packs are useful execution discipline. They are not required ETHOS
substrate.

ETHOS MUST NOT:

- vendor third-party method-pack bodies;
- depend on a method pack as package runtime;
- make a method pack a precondition for repository governance;
- treat method-pack artifacts as proof without promotion into ETHOS evidence.

ETHOS MAY:

- recognize an installed method pack as an optional adapter;
- record whether a method pack was used for a plan or review;
- map the same discipline to ETHOS-native plan/proof/verification gates;
- allow alternative method packs that satisfy the same evidence contract.

Acceptance evidence:

- agent/skill docs describe method packs as replaceable;
- no runtime dependency or vendored copy appears in package metadata;
- method-pack usage never satisfies claim proof by itself.

## P1 Work Package: Quality, Format, Architecture, And Supply Hygiene

Quality additions extend the current hard floor without producing a second
quality authority.

Deliverables:

1. Keep dependency hygiene active through `deptry` package-local owner gates.
1. Keep prose spelling active through `codespell` report-first checks.
1. Keep JSON Schema metaschema hygiene active through `check-jsonschema`.
1. Keep the native `uv audit --frozen` vulnerability gate active against
   `uv.lock` through its repository-owned script and OSV evidence boundary.
1. Activate image/package scanning or external signing only after pinned
   tool supply, owner configs, runner scripts, CI projections, and proof coverage
   exist.
1. Keep fail-closed file-format admission for Python, Markdown, TOML, YAML,
   JSON, shell, and ecosystem-native formats; an unregistered executable carrier
   or a carrier outside its declared home blocks rather than merely reporting.
1. Add a source-owned architecture model and generated diagram projection only
   when it proves value over existing documentation.
1. Add architecture projection drift checks so generated diagrams cannot become
   unreviewed truth.
1. Add semantic-owner or redundancy audits only when they produce actionable,
   bounded findings.

Acceptance evidence:

- every active tool has `system/tools.toml`, config owner, reusable gate, CI/hook
  projection, and proof coverage;
- architecture artifacts are projections and can be regenerated from tracked
  source;
- no generated diagram overrides source/docs/OpenSpec truth.

## P1 Work Package: Evidence Operations

ETHOS should strengthen practical evidence operations generically:

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
1. Add provider artifact observation capture for supported hosted providers.

Deferred non-goals for this plan: external signing upload, image/package
scanning, and OSV scanner activation remain separate Work Lanes until tool
supply, owner configs, runner scripts, CI projections, and proof coverage exist.

Acceptance evidence:

- runbook registry drift is checked;
- MCP smoke logs are evidence artifacts, not truth stores;
- release profile can emit SBOM/provenance/signature evidence without requiring
  adopters to use the same release substrate.

## Non-Adoption Decisions

| Tool class | Decision | Reason |
| --- | --- | --- |
| Environment runners | Optional profile adapter | Too strong as universal ETHOS runtime. |
| Graph build systems | Optional graph/changed-scope adapter | No proven core-scale graph need yet. |
| Task ledgers | Optional task/intake adapter | Task UI must not own Change/Claim lifecycle. |
| Method packs | Optional adapter | Replaceable agent discipline, not repository truth. |
| Broad policy suites | Mine checks only | A copied suite would create a parallel command plane. |

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
