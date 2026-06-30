---
subject: ethos:capability-parity-ledger
role: governance-ledger
state: active
relations:
  canonical_for: product migration parity and adopter switch readiness
---

# Capability Parity Ledger

This ledger classifies capabilities across:

```text
alphasim-dmgr embedded ETHOS
~/projects/ethos product ETHOS
```

The executable product view is available through:

```bash
ethos parity ledger --json
ethos parity gaps --adopter <name> --json
ethos parity shadow --target <repo> --json
```

Each row must include source location, target home, migration disposition,
required tests, parity criterion, and rollback impact.

`ethos parity gaps --json` projects unresolved rows into
`data.pending_packages`. Each package keeps the stable gap code and carries the
capability, source location, target home, disposition, required tests, parity
criterion, and rollback impact together. Adopter shadow checks add a
`shadow_parity_pending:<adopter>` package so local planning can continue even
when remote publication is unavailable.

`ethos parity shadow --json` projects planned or executed comparison work into
`data.execution_packages`. Planned runs expose a
`shadow_parity_not_executed:<target>` package with the command list and semantic
dimensions. Executed runs map every failed command or semantic diff gap to a
package with the same gap code, so campaign closeout can report shadow parity
without relying on remote publication.

Executed shadow comparisons run product ETHOS against the target repository and
the embedded adopter ETHOS in the target's pixi environment. Embedded targets
may declare pixi either with `pixi.toml` or with `[tool.pixi.*]` tables in
`pyproject.toml`. Product commands use `--root` when the command supports it and
fall back to `cwd=<target>` for projection commands that intentionally do not
accept a root option. The semantic projection normalizes legacy embedded
payloads that omit top-level `state` for read-only ready/planned commands.

Executed comparisons also expose `accepted_differences` when a mismatch belongs
to a known cross-generation projection boundary rather than to adopter command
semantics. Product self-audit gaps reported by an external product command are
classified separately when the embedded command has no corresponding gap, so
shadow parity does not mistake ETHOS product-repository maturation work for an
adopter backend mismatch. Legacy changed-scope playbook route gaps are likewise
classified only when the embedded route confirms `changed_path_count=0`. Any
non-self-audit proof gap, mutation/admission gap, embedded gap, command failure,
or changed-scope route gap with actual changed paths remains a blocking
`shadow_diff:*` or command failure package.

## Classification Vocabulary

- already-in-product: the product repository already owns the generic
  capability.
- migrate-to-product: a generic mechanism exists in alphasim-dmgr and must move
  to ETHOS product truth.
- adopter-profile-only: the capability is generic profile glue and remains in
  adopter configuration or thin profile code.
- adopter-domain-only: the capability is dmgr-specific domain governance and
  must not enter product core.
- obsolete: the capability should be retired.
- split: part of the capability migrates and part remains adopter-specific.
- reference-only: the embedded implementation remains a comparison or rollback
  reference.

## Ledger

| Capability | Source location | Target home | Migration disposition | Required tests | Parity criterion | Rollback impact |
| --- | --- | --- | --- | --- | --- | --- |
| status | product and embedded CLI/status paths | `ethos-repository` + Git adapter | split | golden JSON and shadow diff | same branch role, cleanliness, mutation allowance, and gaps | embedded status remains fallback |
| plan | product planner and embedded proof/planner paths | `ethos-repository` | migrate-to-product | changed-scope fixtures | same subjects, contracts, risk classes, gates, and why explanations | embedded plan used for diff |
| prove | embedded proof package and product gate runner | `ethos-repository` + `ethos-test` | migrate-to-product | proof-run fixtures and evidence digest checks | same required gaps, HEAD binding, gate verdict, and evidence refs | embedded proof remains rollback |
| land | Git/lane transition paths | `ethos-repository` + Git adapter | split | dry-run and apply-admission tests | same authorization, expect-head, lane, and candidate transition decision | embedded land disabled unless selected |
| publish | release and remote publication paths | `ethos-repository` + Git/GitLab adapters | split | readiness and no-push tests | same review export, protected mirror, break-glass, tag, and hosted CI requirements | embedded publish remains fallback |
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
| npm launcher design | product `ethos-node` package | `distributions/npm` | migrate-to-product | launcher smoke and no-second-implementation tests | npm only launches Python command plane | launcher can be disabled |
| dmgr raw/cache/conf/alphasim rules | alphasim-dmgr `rules/dmgr` and profile adapters | adopter profile only | adopter-domain-only | dmgr adapter fixture and gate mapping tests | generic ETHOS plans dmgr gates without hardcoding domain details | embedded dmgr gates remain fallback |

## Use

No adopter backend switch can occur until every row has an explicit target home,
migration disposition, parity criterion, and rollback impact. New capabilities
must be added to this ledger before migration work begins.
