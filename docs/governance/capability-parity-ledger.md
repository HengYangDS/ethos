---
subject: ethos:capability-parity-ledger
role: ledger
state: active
relations:
  canonical_for: product migration parity and adopter switch readiness
---

# Capability Parity Ledger

This ledger classifies capabilities across:

```text
reference-adopter embedded governance
ETHOS product governance
```

The executable product view is available through:

```bash
ethos parity ledger --json
ethos parity gaps --adopter <name> --json
ethos parity shadow --adopter <name> --target <repo> --json
```

Each row must include source location, target home, migration disposition,
required tests, parity criterion, and rollback impact.

`ethos parity gaps` is evidence-driven. A migration or split row remains a
required gap until tracked parity evidence under `evidence/parity/` names
that capability in `verified_capabilities` and the adopter shadow report has
`shadow.ok=true` with no required gaps. Changing the ledger disposition alone
does not close a parity gap.

`ethos parity gaps --json` projects unresolved rows into
`data.pending_packages`. Each package keeps the stable gap code and carries the
capability, source location, target home, disposition, required tests, parity
criterion, and rollback impact together. Adopter shadow checks add a
`shadow_parity_pending:<adopter>` package until tracked shadow evidence closes
the adopter-specific gap.

Reference-adopter parity evidence uses repository-local identifiers and
paths supplied by the adopter profile:

```bash
ethos parity gaps --adopter <adopter-id> --json
ethos parity shadow --adopter <adopter-id> --target <repo> --execute --timeout-seconds 30 --json
ethos parity shadow --adopter <adopter-id> --target <repo> --execute --write-evidence --timeout-seconds 30 --json
```

The tracked evidence file is `evidence/parity/<adopter-id>-shadow.json` unless
the adopter profile declares a different evidence target.

Reference adopters are evidence and profile fixtures, not product ontology.
Adopter-private terms may appear in parity evidence, profile fixtures, and this
ledger row when they identify the reference boundary. Product packages and
canonical contracts stay in the generic vocabulary of subjects, claims,
capabilities, gates, evidence, promotion, and providers. The
`reference_adopter_profile_fixture` in `ethos-test` keeps adopter terms inside a
fixture boundary and leaves `core_product_terms` empty.

Tracked shadow parity evidence must carry shadow parity evidence freshness
fields before it can close an adopter gap. The freshness identity records the
product head that produced the evidence, the adopter target `target_head`, and
the `command_sha256` of the recorded shadow command. ETHOS uses these fields to
distinguish a reviewed local evidence artifact from a path-only or date-only
claim. When a target repository is available, campaign closeout compares the
tracked `target_head` with the target's current HEAD before treating the
evidence as matched.

Campaign closeout reports the source of the shadow verdict through provenance
modes rather than through vendor-specific workflow state. `tracked_evidence`
means the verdict came from `evidence/parity/`; `planned_shadow_run` means
no matching evidence has been consumed and the report is only planning a local
run; `live_shadow_run` is reserved for a closeout package that embeds a fresh
in-process shadow run. Remote publication remains a separate deferred package
and does not make local evidence fresher.

`ethos parity shadow --json` projects planned or executed comparison work into
`data.execution_packages`. Planned runs expose a
`shadow_parity_not_executed:<target>` package with the command list and semantic
dimensions. Executed runs map every failed command or semantic diff gap to a
package with the same gap code, so campaign closeout can report shadow parity
without relying on remote publication.

Executed shadow comparisons run product ETHOS against the target repository and
the embedded adopter ETHOS through an explicit backend profile. Supported
embedded backends are `pixi`, declared by `pixi.toml` or `[tool.pixi.*]` tables
in `pyproject.toml`, and `uv-workspace`, declared by `[tool.uv.workspace]`.
Targets without either profile report `embedded_backend_missing` and a
`backend.kind = "missing"` result instead of silently selecting a fallback.
Product commands use `--root` when the command supports it and use
`cwd=<target>` for projection commands that intentionally do not accept a root
option. The semantic projection normalizes historical embedded payloads that omit
top-level `state` for read-only ready/planned commands.

Executed comparisons also expose `accepted_differences` when a mismatch belongs
to a known projection boundary rather than to adopter command semantics. Product
repository-audit gaps reported by an external product command are classified
separately when the embedded command has no corresponding gap, so shadow parity
does not mistake ETHOS product-repository maturation work for an adopter backend
mismatch. Changed-scope playbook route gaps, including strict activation-version
gaps, are classified only when the embedded route confirms
`changed_path_count=0`. `ethos report` parity freshness gaps are classified only
for the evidence-refresh bootstrap case, where the current shadow run is the
operation that can replace stale tracked evidence. Any non-repository-audit
proof gap, mutation/admission gap, embedded gap, command failure, or
changed-scope route gap with actual changed paths remains a blocking
`shadow_diff:*` or command failure package.

Executed reports include `accepted_summary` at report level and per comparison
so closeout can see accepted counts, affected command count, and counts by kind
without scanning every raw payload. The `shadow-parity.schema.json` contract
validates the accepted-difference record shape, allowed kinds, command context,
and summary counters. Dated evidence under `evidence/chronicle/` records the current
accepted classification boundary without treating it as remote publication.

Tracked shadow evidence is closeout input only when its identity is fresh. The
evidence record must bind the adopter id, target path, product HEAD, target
HEAD, command digest, full command identity, command list, semantic dimensions,
verified capabilities, capability basis, shadow accepted-difference summary, and
zero false-negative count. The `external_false_negative` semantic dimension is
mandatory: external ETHOS may report a stricter required-gap superset, but it
must not miss an embedded blocking gap or move it into advisory-only state.
If any of the identity fields are missing, stale, target-mismatched, or produced
by an old command shape, ETHOS reports a blocking `parity_evidence_refresh`
package. The package names the adopter, product root, explicit target when
supplied, required gaps, and the exact refresh command:

When the commit that last changed a tracked evidence file is the current product
or same-repository target commit, the commit parent is also an acceptable
freshness head. This keeps local evidence commits verifiable without allowing
stale adopter targets: cross-repository adopters still require exact target HEAD
matching.

```bash
ethos parity shadow --adopter <adopter-id> --target <repo> --execute --write-evidence --json
```

When no target is supplied, ETHOS leaves the target as `<repo>` rather than
reusing a stale path from old evidence.

## Classification Vocabulary

- already-in-product: the product repository already owns the generic
  capability.
- migrate-to-product: a generic mechanism exists in reference-adopter and must move
  to ETHOS product truth.
- adopter-profile-only: the capability is generic profile glue and remains in
  adopter configuration or thin profile code.
- adopter-domain-only: the capability is domain-specific governance and
  must not enter product core.
- obsolete: the capability should be retired.
- split: part of the capability migrates and part remains adopter-specific.
- reference-only: the embedded implementation remains a comparison or rollback
  reference.

## Ledger

| Capability | Source location | Target home | Migration disposition | Required tests | Parity criterion | Rollback impact |
| --- | --- | --- | --- | --- | --- | --- |
| status | product and embedded CLI/status paths | `ethos-repository` Git-native semantics + execution adapter | split | golden JSON and shadow diff | same branch role, cleanliness, mutation allowance, and gaps | embedded status remains fallback |
| plan | product planner and embedded proof/planner paths | `ethos-repository` | migrate-to-product | changed-scope fixtures | same subjects, contracts, risk classes, gates, and why explanations | embedded plan used for diff |
| prove | embedded proof package and product gate runner | `ethos-repository` + `ethos-test` | migrate-to-product | proof-run fixtures and evidence digest checks | same required gaps, HEAD binding, gate verdict, and evidence refs | embedded proof remains rollback |
| land | Git/lane transition paths | `ethos-repository` Git-native semantics + execution adapter | split | dry-run and apply-admission tests | same authorization, expect-head, lane, and candidate transition decision | embedded land disabled unless selected |
| publish | release and remote publication paths | `ethos-repository` Git-native semantics + hosted-provider adapters | split | readiness and no-push tests | same review export, protected mirror, break-glass, tag, and hosted CI requirements | embedded publish remains fallback |
| report | product report and embedded scorecards | `ethos-repository` | migrate-to-product | scorecard golden output | same governance, evidence, command-surface, and projection health verdicts | embedded report used for diff |
| SQLite state | product local state and embedded host/runtime state | `ethos-adapters` SQLite + repository logical model | split | migration and ignored-state tests | same leases, events, gate runs, sessions, and ignored truth boundary | state stays host-local |
| OpenSpec | product `openspec/` and embedded spec adapter | `ethos-adapters` official OpenSpec + `ethos-contracts` | split | official CLI validation and lifecycle fixtures | official CLI validates specs and changes; no ad hoc replacement | embedded adapter remains reference |
| Backlog / intake | embedded intake/backlog adapters | `ethos-repository` + Backlog adapter | migrate-to-product | backlog fixture and adapter contract tests | same intake status, task mapping, and board projection | embedded intake remains oracle |
| campaign / mission | embedded campaign package and product evolution docs | `ethos-repository` | migrate-to-product | hypothesis lifecycle fixtures | same opportunity, hypothesis, challenge, exhaustion, and closeout states | embedded campaign remains oracle |
| SQLite proof/evidence index | embedded runtime/proof/evidence paths | `ethos-repository` + `ethos-adapters` | split | evidence freshness fixtures | same digest, HEAD binding, durability, and claim refs | embedded evidence remains reference |
| command surface | product registry and embedded command-plane policies | `ethos-contracts` + `ethos-repository` | migrate-to-product | docs command vocabulary tests | retired roots never appear as public current workflow | embedded policies guide migration |
| assistant boundaries | product assistant package and embedded agent/host packages | `ethos-assistants` | split | projection contract fixtures | same truth/projection/context classification | embedded host checks remain reference |
| MCP / ACP / Superpowers | product agent projection and embedded host package | `ethos-assistants` + adapters | split | method-pack and protocol manifest tests | same external method pack, host-local context, and protocol projection boundaries | embedded host remains oracle |
| quality determinism | product governance checks and embedded quality package | `ethos-repository` + adapters | migrate-to-product | format, artifact, command, and evidence policy fixtures | same required gates and deterministic policies | embedded quality remains reference |
| Hatchling local build | embedded Hatchling package metadata and product metadata | all Python packages | already-in-product | `uv build --all-packages` | all Python packages build wheel and sdist locally | no remote release needed |
| npm launcher design | npm launcher distribution adapter | `distributions/npm` | migrate-to-product | launcher smoke and no-second-implementation tests | npm only launches Python command plane | launcher can be disabled |
| domain data-contract rules | reference-adopter `rules/domain` and profile adapters | adopter profile only | adopter-domain-only | domain adapter fixture and gate mapping tests | generic ETHOS plans domain gates without hardcoding domain details | embedded domain gates remain fallback |

## Use

No adopter backend switch can occur until every row has an explicit target home,
migration disposition, parity criterion, and rollback impact. New capabilities
must be added to this ledger before migration work begins.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
