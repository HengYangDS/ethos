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
    -> CLI, template, provider, or evidence adapter
```

Python owns IO boundaries, compilation, pure reduction, and adapters. TOML owns
durable declarations. CEL owns bounded predicates over typed facts. `graphlib`
owns graph ordering and cycle detection. Jinja owns projection rendering with a
typed context. A projection never becomes truth merely because it was rendered.

## Baseline And Non-Evasion Rule

The execution baseline is the parent of this Work Lane:

```text
head: 2dab77f169eceb2d45f917358c2a7487e7ac8db6
global effective executable source: 105,342
all tracked Python effective source: 83,889
```

`global_effective` counts tracked, maintained executable carriers: product and
test Python, tools, shell, JavaScript, TOML, YAML, JSON/JSON Schema, INI, Jinja,
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
active debt may not exceed 5% of the baseline (5,267 effective lines). A baseline
cannot be reset, a debt cannot be silently extended, and splitting a file or
moving logic to a declaration does not satisfy this program.

The active `program-foundation` record is capped at 1,200 lines: 350 product
Python, 400 test Python, 250 tool Python, and 200 TOML. The tool allowance is
only for T2's formal-provider execution adapter: independent Git-worktree
materialization, Docker-context binding, and provider evidence. T3--T8 must
settle it by compiling that adapter into the shared declaration/projection spine
and deleting its redundant test and runner branches. The aggregate record remains
capped at 1,200; no category allowance is an independent expansion right.

## Final Technical Choices

| Concern | Chosen mechanism | Boundary |
| --- | --- | --- |
| Public contracts and declarations | Pydantic v2 strict frozen models | Nested state uses frozen children, tuples, or readonly boundaries; mutable dictionaries are not immutable contracts. |
| Graphs | Python `graphlib` | No bespoke topological sorter or cycle walker. |
| Predicates | `cel-python`, restricted CEL subset | Pure typed facts only; no IO, mutation, dynamic imports, reflection, or unbounded user functions. |
| CLI | Cyclopts plus declaration-first command registry | Manual handlers only bind an adapter or carry a bounded migration. |
| Templates | Jinja2 plus typed context and `StrictUndefined` | Rendered output is checked by the target carrier tool. |
| Functional form | Pure reducers and explicit typed results | No DI/effect framework, `returns`, persistent-map abstraction, or second result hierarchy. |
| Property testing | Hypothesis | Used where it replaces scenario enumeration; its database is runtime state. |
| Duplication control | AST-native redundancy, forwarder, re-export, and semantic-owner checks | No perpetual jscpd/vulture allowlist. |

NetworkX, OPA/Rego, Temporal, Dagster, Airflow, CUE, Jsonnet, Dhall, Nickel,
Copier, Cookiecutter, `returns`, Pyrsistent, immutables, Nox, Pixi, Allure, and
Testcontainers are intentionally outside the product. They add a runtime,
parallel authority, or framework surface without a demonstrated net deletion.

## Carrier Admission And Quality Contract

No executable carrier may be introduced without one owner, a format or explicit
formatter exception, syntax validation, semantic validation, behavior proof,
runtime-cache home, supply-chain owner, and a named gate.

| Carrier | Canonical checks |
| --- | --- |
| Python | Ruff format/lint, `ty`, architecture and redundancy checks, pytest and Hypothesis, focused Semgrep |
| TOML | Taplo format/lint, Pydantic parse, reference and compiler validation |
| YAML | Prettier, yamllint, actionlint/zizmor or GitLab execution as applicable |
| JSON and JSON Schema | Prettier `--check`, `check-jsonschema`, schema fixtures and Pydantic round trips |
| Shell | shfmt, ShellCheck, explicit exit-code contract smoke |
| JS/MJS | Prettier, ESLint, `node --check`, npm clean-install smoke |
| Jinja | AST parse, typed context, `StrictUndefined`, deterministic render; then target-carrier formatter/linter |
| Markdown | Prettier, markdownlint-cli2, lychee, codespell |
| Mermaid/C4 | deterministic `mmdc` render/syntax validation |
| INI | no new files; migrate the remaining files to TOML during cleanup |

Jinja and Mermaid do not receive a source formatter merely to satisfy a checklist:
`djLint` is unsuitable for ETHOS's non-HTML templates, and Mermaid has no stable
general formatter. Their output or renderer is the canonical form. This is an
explicit exception, not an unowned format.

All Python and Node tools are locked repository dependencies, not global-machine
assumptions. Dependency admission records the replacement, import and lock impact,
cold-start cost, version, checksum where relevant, vulnerability surface, deletion
plan, and rollback. Supply-chain proof uses `uv lock --locked`, `npm ci
--ignore-scripts`, deptry, pip-audit, npm audit, Syft SPDX SBOM, Grype, gitleaks,
Semgrep, package checks, and reproducible-build hashes. OSV scanning and Trivy do
not join the default floor because this set already covers locks and artifacts.

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
| Fast changed-scope | formatting, lint/type, declaration semantics, source budget, redundancy, focused unit/property proof |
| Local provider | actual selected `act` and `gitlab-ci-local` jobs for changed provider paths |
| Nightly | full property corpus, bounded mutation tests for pure reducers/CEL, benchmarks, full Semgrep and SBOM scan |
| Release | locks, clean install, package artifacts, two-build hash, SBOM/Grype, full provider subset |
| Closeout | HEAD-bound proof plus proof that old implementation and its dedicated tests/tools/declarations were deleted |

## Completion Definition

The program is complete only when the two terminal source budgets pass on `dev`,
all category budgets are non-growing, all temporary debt is settled, carrier
admission is fail-closed, local provider evidence executes real jobs, and every
declarative migration has removed the mechanism it replaced.
