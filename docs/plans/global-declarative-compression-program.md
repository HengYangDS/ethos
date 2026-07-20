---
subject: ethos:global-declarative-compression
role: plan
state: active
relations:
  canonical_for: global source compression, declarative-runtime migration, and quality-carrier admission
  derives_from: terminal-governance-product-design, declarative-runtime-spine-modernization, global-declarative-compression-program-20260711
---

# Global Declarative Compression Program

Status: active program plan.

Purpose: reduce the whole maintained executable surface of ETHOS while making
the resulting system more declarative, typed, functional, and verifiable. This
is not a Python-only refactor and it is not a plan to conceal procedure in
configuration or generated files.

See also: [Terminal Governance Product Design](terminal-governance-product-design.md),
[Declarative Runtime Spine Modernization](declarative-runtime-spine-modernization.md),
and [Declarative Governance Compiler](../architecture/declarative-governance-compiler.md).

## Fixed Outcome

ETHOS keeps one repository-governance kernel and one public command plane:

```text
status -> plan -> prove -> land -> publish
```

It does not adopt a workflow platform, policy server, effect system, or a second
truth store. The terminal shape is instead:

```text
adapter / IO
    -> strict typed facts
    -> pure reducer, compiler, and graph kernel
    -> immutable typed projection
    -> CLI, serializer, provider, or evidence adapter
```

Python owns IO boundaries, compilation, pure reduction, and adapters. TOML owns
durable declarations. CEL owns bounded predicates over typed facts. `graphlib`
owns graph ordering and cycle detection. Native serializers own unavoidable
external leaves. A projection never becomes truth merely because it was emitted.

## Baseline And Non-Evasion Rule

The execution baseline is the parent of this Work Lane:

```text
head: 2dab77f169eceb2d45f917358c2a7487e7ac8db6
global effective executable source: 105,342
all tracked Python effective source: 83,889
```

`global_effective` counts tracked, maintained executable carriers: product and
test Python, tools, shell, JavaScript, TOML, YAML, JSON/JSON Schema, INI,
and diagrams. It excludes prose, evidence, caches, binaries, and lockfiles. A
tracked generated projection remains counted unless it is separately reported as
reproducible derived output; it never makes its source disappear from the metric.

The terminal budgets are:

| Metric | Baseline | Terminal maximum |
| --- | ---: | ---: |
| Global executable effective source | 105,342 | 73,739 |
| All tracked Python effective source | 83,889 | 58,722 |

No carrier category may finish above baseline. `scc` is an independent inventory
and drift detector; it is not combined with the Python AST-aware metric.

Temporary additions require a tracked compression-debt record with an owner,
replacement, exact deletion wave, expiry, and expected net deletion. Aggregate
active debt may not exceed the declared append-only cap. The current integrated
candidate train originally set that cap to 8,163 effective lines; the current
ledger has retired expired records and retains only 165 effective lines of
live, independently dated debt. Changing it requires a
separate governed reconciliation, never an implicit baseline reset. A baseline
cannot be reset, a debt cannot be silently extended, and splitting a file or
moving logic to a declaration does not satisfy this program.

The active debt is now globally capped at the declared 165 effective lines.
It is not a baseline reset and it never changes either terminal budget.
`program-foundation`
is the bounded measurement, compiler, and archival-evidence record. Its 14
effective TOML lines for the accepted claim/archive binder, two effective JSON
lines for refreshed generic parity evidence, and two product-Python effective
lines that preserve compact-report governance context are explicit foundation
debt, not an uncounted documentation escape. The separate
`candidate-train-reconciliation` record is a measured integration allowance for
already-admitted candidate-train capabilities that arrived while this program
was being rebased: independent verification, performance evidence, native proof
bootstrap, runtime binding, and lane-resolution receipts. It expires in T8 and must be deleted by
consolidating their scenario tests, runner wrappers, templates, and provider
copies; it is not permission to retain duplicate behavior.

The reconciliation record is exact rather than aspirational. The current
candidate-train reconciliation snapshot bounds 1,344 product-Python, 1,970
test-Python, 347 other-Python, 368 shell, 4 YAML, 102 JSON, and 15
Jinja effective lines. Those original records were later joined by independently
governed candidate-train debt records. The live policy, not this historical
subtotal, was the historical allowance SSOT. Expired records were deleted rather
than extended; current measurement remains visible as Campaign growth advisory.
The recorded snapshot remains **36,268 global** and **29,696
Python** effective lines above the terminal maxima; T8 and T9 cannot close while
any of that gap or active debt remains.

During this program the source-budget policy uses `campaign_terminal`
enforcement: Change-local source growth is measured but does not mechanically
block iteration while the Campaign remains active. Configuration errors,
debt-cap overflow, expired debt, and stale debt remain local blockers. Terminal
targets and zero active debt remain mandatory at Campaign closeout and before
the single dual-remote publication.

## Final Technical Choices

| Concern | Chosen mechanism | Boundary |
| --- | --- | --- |
| Public contracts and declarations | Pydantic v2 strict frozen models | Nested state uses frozen children, tuples, or readonly boundaries; mutable dictionaries are not immutable contracts. |
| Graphs | Python `graphlib` | No bespoke topological sorter or cycle walker. |
| Predicates | `cel-python`, restricted CEL subset | Pure typed facts only; no IO, mutation, dynamic imports, reflection, or unbounded user functions. |
| CLI | Cyclopts plus declaration-first command registry | Manual handlers only bind an adapter or carry a bounded migration. |
| Serialization | Carrier-native serializer over a strict typed declaration | Generated leaves must be externally required and checked by the target carrier tool. |
| Functional form | Pure reducers and explicit typed results | No DI/effect framework, `returns`, persistent-map abstraction, or second result hierarchy. |
| Property testing | Hypothesis | Used where it replaces scenario enumeration; its database is runtime state. |
| Duplication control | AST-native redundancy, forwarder, re-export, and semantic-owner checks | No perpetual jscpd/vulture allowlist. |

NetworkX, OPA/Rego, Temporal, Dagster, Airflow, CUE, Jsonnet, Dhall, Nickel,
Jinja2 rendering or scaffold generation, Copier, Cookiecutter, `returns`,
Pyrsistent, immutables, Nox, Pixi, Allure, and Testcontainers are intentionally
outside the product. The only admitted Jinja2 surface is the parse-only Budget
Contract v2 measurement provider; it never renders templates or owns adoption
scaffolding. The excluded mechanisms add a runtime, parallel authority, or
framework surface without a demonstrated net deletion.

## Carrier Admission And Quality Contract

No executable carrier may be introduced without one owner, a format or explicit
formatter exception, syntax validation, semantic validation, behavior proof,
runtime-cache home, supply-chain owner, and a named gate.

| Carrier | Canonical checks |
| --- | --- |
| Python | Ruff format/lint, `ty`, architecture and redundancy checks, pytest and Hypothesis, focused Semgrep |
| TOML | Taplo format/lint, Pydantic parse, reference and compiler validation |
| YAML | yamllint, actionlint/zizmor or GitLab execution as applicable |
| JSON and JSON Schema | jq canonical formatting, check-jsonschema, schema fixtures and Pydantic round trips |
| Shell | shfmt, ShellCheck, explicit exit-code contract smoke |
| JS/MJS | ESLint, `node --check`, npm clean-install smoke |
| Markdown | markdownlint-cli2, lychee, codespell |
| Mermaid/C4 | deterministic `mmdc` render/syntax validation |
| INI | no new files; migrate the remaining files to TOML during cleanup |

Mermaid does not receive a source formatter merely to satisfy a checklist; its
deterministic renderer is the canonical check. This is an explicit exception,
not an unowned format.

All Python and Node tools are locked repository dependencies, not global-machine
assumptions. Dependency admission records the replacement, import and lock impact,
cold-start cost, version, checksum where relevant, vulnerability surface, deletion
plan, and rollback. Supply-chain proof uses `uv lock --locked`, `npm ci
--ignore-scripts`, deptry, uv audit, npm audit, Syft SPDX SBOM, Grype, gitleaks,
Semgrep, package checks, and reproducible-build hashes. Separate OSV and Trivy
clients do not join the default floor because native uv audit already covers the
Python lock and this set already covers artifacts.

## CI Provider Parity

The existing `act ... --list` and `gitlab-ci-local ... --list` paths are discovery
only. They cannot produce a passing local-provider claim.

The program introduces a declaration of emulatable jobs. Each entry records the
formal workflow, event, job, image mapping, supported inputs, and any exact
hosted-only reason. The owner runner then executes:

```text
act -W <formal workflow> <event> -j <job>
gitlab-ci-local --file .gitlab-ci.yml <job>
```

The local evidence records HEAD, executed job, image digest, tool versions,
redacted inputs, and result. A job that cannot be represented faithfully is
`hosted-observation-only`, never locally green by omission. Provider YAML remains
thin orchestration over the same owner scripts; it does not copy quality policy.

## Migration Waves

Every wave follows the same destructive sequence:

```text
generic mechanism -> old/new parity -> cutover -> delete old production code
-> delete old tests, fixtures, scripts, declarations, and provider copies
-> source-budget delta -> debt settlement
```

The archived `global-declarative-compression-program-20260711` OpenSpec carrier
records only the measured foundation and its completed vertical slices; it does
not close a numbered wave wholesale. This plan remains the program SSOT, but
every remaining wave or unfinished wave portion must begin in a fresh owned Work
Lane with one bounded claim and one phase-specific OpenSpec carrier. That carrier
must be archived before landing; no active future-phase carrier may be promoted
merely because this plan names its intended outcome.

### T0 — Measurement And Compression Debt

Add the source-budget model, carrier classifier, debt ledger, `scc` cross-check,
AST redundancy/forwarder/re-export checks, stale-allowlist detection, and
semantic-owner ban. Exit only when a declared change cannot claim compression
without a repository-wide delta.

### T1 — Carrier And Tool Admission

Make format selection fail closed and wire the carrier matrix into reusable owner
scripts, config, tool catalog, CI, hooks, and proof selection. Move all new tool
state to `build/runtime` or `build/evidence`.

### T2 — Real Local Provider Execution

Replace emulator listing as a pass condition with selected-job execution and
explicitly model hosted-only gaps. Do not delete provider adapters merely because
they are projections.

### T3 — Typed Declaration And Projection Compiler

Introduce one declaration-to-contract-to-compiler-to-immutable-projection path.
First consumers are duplicated result envelopes, gaps, next actions, and summary
models. Delete manual builders after parity.

### T4 — CEL Topology Vertical Slice

Move hand-written topology and policy predicate chains into restricted CEL over
typed facts, keeping ordering in `graphlib`. Require compile, fact-scope,
reachability, dead-rule, parity-corpus, and property tests. Delete the old chain;
dual-run cannot become a permanent architecture.

### T5 — Policy And Read-Model Convergence

Compile quality, policy, status, orient, and report projections instead of
reassembling dictionaries. Preserve output contracts while deleting duplicate
builders, snapshots, and adapters.

### T6 — Lifecycle State-Machine Convergence

Express legal lane, handoff, resolution, claim, and evidence transitions as
declarations plus pure reducers. Retain imperative code only at persistence,
Git, and external-adapter boundaries.

### T7 — Command Registry Convergence

Make command parameters, output contracts, exit mapping, authority, and adapter
binding registry-first. Cyclopts stays as a binding layer. Retire aliases,
forwarders, manual help assembly, and duplicate command tests.

### T8 — Test, Tool, And Template Settlement

Replace enumerative test copies with scenario matrices, parameterization, and
properties. Remove obsolete fixtures, helper modules, scripts, templates, INI,
and compatibility paths only after behavioral parity, coverage, and mutation
evidence show no loss.

### T9 — Terminal Deletion Settlement

No dual-run, compatibility shim, expired debt, stale allowlist, hand-maintained
provider copy, or unclassified executable carrier remains. Recalculate budgets
on the final `dev` head; failure to meet both terminal maxima means the program is
not complete.

## Execution Tiers

| Tier | Required scope |
| --- | --- |
| Fast changed-scope | formatting, lint/type, declaration semantics, redundancy, focused unit/property proof; source-budget remains a separately reported global-compression obligation |
| Local provider | actual selected `act` and `gitlab-ci-local` jobs for changed provider paths |
| Nightly | full property corpus, bounded mutation tests for pure reducers/CEL, benchmarks, full Semgrep and SBOM scan |
| Release | locks, clean install, package artifacts, two-build hash, SBOM/Grype, full provider subset |
| Closeout | HEAD-bound full proof including source-budget, plus proof that old implementation and its dedicated tests/tools/declarations were deleted |

## Completion Definition

The program is complete only when the two terminal source budgets pass on `dev`,
all category budgets are non-growing, all temporary debt is settled, carrier
admission is fail-closed, local provider evidence executes real jobs, and every
declarative migration has removed the mechanism it replaced.
