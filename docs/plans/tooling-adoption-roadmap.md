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
  native `uv audit --frozen` lock analysis, C4-like
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
- an executable-mechanism catalog in `system/tools.toml` that contains admitted
  active tools only;
- product-boundary and contributor-policy gates that keep distribution and
  identity organization-native.

## Quality Capability Portfolio

This roadmap is the sole comparison and future-decision surface. The runtime
catalog contains admitted active mechanisms only. A bounded OpenSpec Change owns
pilot config, supply, runner, evidence, and expiry outside that catalog; the tool
enters the catalog only on promotion. Warnings fail just like errors. A tool that
loses a pilot leaves no dependency, config, cache, wrapper, allowlist, or
re-export.

`system/gates.toml` is the gate-set SSOT. Local CI, hooks, GitHub, and GitLab still
contain handwritten projections; the next convergence wave must derive or
validate them against the registry. Tool-native config owns only tool policy.
Version, source, license, digest, cache, network, and write boundaries require a
single tracked supply declaration rather than comments spread across runners.

### Admitted floor

| Capability | Single owner | Boundary |
| --- | --- | --- |
| Change and specification semantics | OpenSpec strict plus ETHOS lifecycle | Official syntax first; ETHOS adds identity, scope, claim, and archive governance. |
| Python format, lint, idioms, cyclomatic complexity, and fast SAST | Ruff | Includes C90, PL, FURB, SLOT, security, exception, and suppression ratchets; no Pylint/Flake8/Black/isort stack. |
| Python types | ty | One locked checker across Python 3.12-3.14; no permanent mypy/Pyright mirror. |
| Import architecture | import-linter | Explicit layer contracts; discovery tools do not replace declared boundaries. |
| Dependency hygiene | deptry | Distribution-local metadata truth; not vulnerability evidence. |
| Test execution | pytest, pytest-timeout, pytest-xdist | Strict config/markers and warnings-as-errors; xdist is scheduling, not concurrency proof, and reruns never convert failure into proof. |
| Concurrency proof | pytest plus deterministic subprocess barriers | Extend the existing real-process harness for lease, handoff, and closeout races; sleep-only tests are not proof. |
| Property and state-space testing | Hypothesis | Own property, state-machine, differential, and metamorphic tests before another invariant DSL is considered. |
| Statement and branch coverage | coverage.py plus pytest-cov | The hard floor remains 100%; coverage proves reachability, not assertion adequacy. |
| TOML | Taplo | Canonical format and lint after supply bootstrap. |
| YAML | yamllint | Strict lint only; no permanent second formatter. |
| JSON and JSON Schema | Python stdlib JSON plus check-jsonschema | Path-selected compact/pretty form and metaschema validation; jq is not a second formatter. |
| Hook configuration | pre-commit validate-config | Syntax and shape validation only; repository-local owner scripts remain the hook policy. |
| Shell lint | ShellCheck | Style warnings fail; tracked scripts and extensionless Git hooks use their declared shebang through one config owner. |
| Markdown, links, spelling, and docs topology | markdownlint-cli2, Lychee, codespell, ETHOS docs gates | Active docs and current OpenSpec changes are governed; immutable archive/evidence remains history, not rewrite material. |
| Blank lines, trailing space, and final newlines | Carrier-native formatters plus repository hygiene | Markdown/YAML/TOML/Python owners enforce their own syntax; no generic reader or EditorConfig clone becomes a second authority. |
| GitHub workflow syntax | actionlint | Syntax and expression owner only; security belongs to zizmor. |
| Provider projections | template drift plus act/gitlab-ci-local adapters | Local execution is not hosted-provider success. |
| MCP projection shape | ETHOS MCP smoke | Configuration presence only; protocol semantics remain unclaimed. |
| Secrets | Gitleaks | One scanner; broad test exclusions must shrink to exact fixtures. |
| Python vulnerabilities | uv audit | Native lock audit remains current; a multi-ecosystem replacement must prove net deletion first. |
| Build and local installation | uv build plus isolated wheel smoke | Artifact contents and reproducibility remain separate future checks. |
| Source budget | ETHOS native measurement | `scc` is an independent inventory sensor, never correctness authority. |
| Release envelopes | ETHOS SPDX-lite and in-toto/SLSA-shaped projections | Local shapes only; no standard-conformance or artifact-signature claim. |

### Bounded pilot queue

External pilots wait behind two native P0 closures: every active trust-bearing
gate must map owner -> descriptor -> proof set -> execution planes, and every
tool supply path must declare version, source, digest, cache, network, write, and
license boundaries. A check-only runner must never install or update its tool.

| Priority | Capability | Incumbent | Promotion or terminal exit |
| --- | --- | --- | --- |
| P0 | Gate-plane compilation | `system/gates.toml` plus native projection compiler | Delete copied commands from hooks/local/GitHub/GitLab; do not add a task runner. |
| P0 | Repository asset closure | `git ls-files`, shebangs, and the format registry | Every tracked carrier maps to one asset class and owner or an explicit not-applicable decision; gate self-enumeration is insufficient. |
| P0 | CI binary supply compression | Aqua, CI projection only | Replace and delete admitted download/checksum installers; local macOS remains Brew-admitted and no Aqua task/environment plane is allowed. |
| P0 | Suppression debt | Existing Ruff, type, and coverage owners | Count `fmt`, `noqa`, type ignores, `pragma: no cover`, and coverage exclusions with exact reasons and a declining baseline; no second linter. |
| P0 | Dev-tool dependency reachability | Existing dependency-hygiene owner | Every root dev requirement maps to a source import, pytest plugin, owner executable, or declared tool identity; remove unmapped names rather than add a second dependency scanner. |
| P0 | Runtime compatibility | uv-managed CPython 3.12, 3.13, and 3.14 matrix | One owner script projects identically to GitHub and GitLab; a 3.14-only sensor cannot stand in for compatibility. |
| P0 | Dual-forge distribution parity | registry-derived provider jobs | Python and npm build/test/release capabilities must exist on both forges; provider status remains separate. |
| P0 | GitHub workflow security | zizmor | Pin Actions to immutable commits and remove real findings; otherwise reject with no config. |
| P0 | Clone-driven compression | find-dup-defs diagnostic pilot | Require pinned supply, repeatable macOS/Linux output, and net deletion on two real changes; otherwise absorb findings and retire. |
| P0 | Stateful lifecycle proof | Hypothesis RuleBasedStateMachine | Replace combinatorial lease/handoff/retire examples and delete superseded tests; no new tool. |
| P0 | Test replay receipt | Existing pytest/Hypothesis owner | Bind HEAD, interpreter, OS, workers, shards, selected node IDs, seed/reproducer, and environment boundary without adding a test-report platform. |
| P1 | Shell canonical form | shfmt | One destructive format convergence, then a check-only gate; reject if supply code or ELOC inflation outweighs consistency. |
| P1 | Mutation adequacy | mutmut | Pure reducers only; promote only if stable survivors expose missing assertions without full-suite cost. |
| P1 | Network isolation | pytest-socket | Default-deny only after explicit network tests are marked; a hidden network dependency is a test failure. |
| P1 | Time-boundary determinism | time-machine | Use only for lease/TTL integration boundaries; retain explicit clock parameters in pure code and forbid autouse freezing. |
| P1 | Unused test fixtures | pytest-deadfixtures | Promote only for deterministic, manually confirmed deletions; dynamic fixture use must not create an allowlist. |
| P1 | Subprocess coverage | coverage.py subprocess patch | Extend the existing owner only for CLI/process subsets; no second coverage tool. |
| P1 | Fault and interruption proof | pytest monkeypatch plus existing process harness | Inject failed rename/write, permission, signal, and child-process boundaries; preserve or replay state and delete weaker examples. |
| P1 | Concurrent-history consistency | Hypothesis model plus native operation-history checker | Validate observed lease/handoff/retire histories against the lifecycle model; do not introduce a distributed-test control plane. |
| P1 | Reproducible packages | two isolated uv/Hatchling builds | Fixed source epoch and equal wheel/sdist hashes; invoke diffoscope only on mismatch. |
| P1 | Semantic repository policy | Semgrep CE | Admit one pinned offline rule only when Ruff/import-linter cannot express it; no independent finding means reject. |
| P1 | Package metadata | validate-pyproject | Warnings, missing license/project URLs, and placeholder public-distribution URLs are failures; promote only if it catches defects before uv build. |
| P1 | Built distribution metadata | `twine check --strict` | Inspect actual wheel/sdist rendering; reject if validate-pyproject and install smoke already expose every finding. |
| P1 | Wheel contents | check-wheel-contents | Post-build, check-only; promote only if it adds value beyond install smoke. |
| P1 | npm package correctness | publint | Run against the packed thin launcher; reject if it adds no finding beyond `npm pack --dry-run` and native smoke. |
| P1 | MCP protocol conformance | official MCP conformance suite | Own protocol behavior and delete overlapping semantic smoke; keep the current projection-only check separate. |
| P1 | Documentation terminology | Vale | Product docs only; prove value for controlled vocabulary without policing archives or Chinese prose incorrectly. |
| P1 | Standard SBOM | Syft | Replace and delete the native SPDX-lite builder/tests after parity; never coexist permanently. |
| P1 | SBOM conformance | SPDX tools-python | Validate the admitted SPDX output; generation and conformance remain separate capabilities. |
| P1 | File-level licensing | REUSE | Prefer one bounded repository metadata declaration over thousands of source headers. |
| P2 | Test-order coupling | pytest-randomly | Use changing scheduled seeds, retain the failing seed, and reproduce exactly; promote only after two real coupling defects. |
| P2 | Performance regression | pytest-benchmark | Serial, opt-in, hardware-labelled evidence; never join the correctness floor. |
| P2 | Artifact vulnerability | Grype | Release profile over the admitted Syft SBOM; it does not duplicate uv lock auditing. |
| P2 | Dependency license policy | Grant over the admitted Syft SBOM | One allow/deny owner after standard SBOM cutover; reject pip-licenses/LicenseCheck in parallel. |
| P2 | GitLab merged-config semantics | GitLab CI Lint API through hosted observation | Bind merged YAML and commit; network/provider success never enters the offline floor. |
| P2 | Provenance and signing | PyPI PEP 740 and npm trusted-publishing attestations; cosign only for detached blobs | Prefer registry-native OIDC on both forges; bind exact subjects, digests, verification, and publication. |

Read-only exploration on 2026-07-23 was admission evidence, not promotion proof.
Vulture reported only the dynamically loaded build hook at high confidence and
flooded on Pydantic/Cyclopts declarations at lower confidence, so a permanent
allowlist would cost more than it deletes. Repeated find-dup-defs output was
byte-stable and exposed a duplicate production helper, making it the current
pilot incumbent rather than an admitted owner. pyscn exposed useful structural
signals, but its raw timestamps, durations, and unstable ordering disqualify it
from clone ownership while the narrower candidate exists.

Primary-source anchors: [Aqua](https://aquaproj.github.io/),
[MCP conformance](https://github.com/modelcontextprotocol/conformance),
[PyPI attestations](https://docs.pypi.org/attestations/),
[npm provenance](https://docs.npmjs.com/generating-provenance-statements/),
[publint](https://publint.dev/),
[Twine](https://twine.readthedocs.io/en/stable/#twine-check),
[GitLab CI Lint](https://docs.gitlab.com/api/lint/),
[Grant](https://github.com/anchore/grant), and
[time-machine](https://time-machine.readthedocs.io/).

### Deferred or on-demand

| Mechanism | Use only when | Why not active |
| --- | --- | --- |
| pyscn | A real cohesion question exists, clone analysis is disabled, and upstream supports the ETHOS Python 3.14 baseline | Overlaps active architecture/complexity owners and needs output normalization. |
| jscpd | A real cross-language lexical clone question appears | Too noisy for Python-first default proof. |
| deadcode | A no-allowlist trial proves materially better precision than Vulture | Whole-program dynamic declarations make dead-code scanners expensive to govern. |
| complexipy | Ruff C901 misses a demonstrated cognitive-complexity defect | A second complexity metric must first prove independent actionability. |
| Griffe | ETHOS declares an explicit supported Python API manifest | Compatibility findings must not freeze incidental public names or justify shims. |
| Tach | Import-linter contracts cannot express a proven boundary | Replacement benchmark only; never a parallel architecture gate. |
| pytest-repeat | Reproducing a known flake | Diagnostic repetition only; no pass-by-rerun. |
| pytest-testmon or pytest-split | Inner-loop selection or CI balancing is measurably slow | Cache-based selection can accelerate iteration but never satisfies final proof. |
| prek | A replacement benchmark proves materially faster hooks and removes the Python pre-commit dependency | Current hooks are local system commands, so a second binary supply path may cost more than it saves. |
| pytest-run-parallel | Free-threaded Python becomes an explicit supported runtime | Thread-safety stress is distinct from xdist, but not current compatibility proof. |
| HypoFuzz | At least three mature Hypothesis properties have stable databases | Reuse the property corpus before adding a fuzz campaign. |
| Atheris | A byte/parser boundary has a retained corpus and crash contract | Native fuzzing cost is unjustified for ordinary reducers. |
| CrossHair | Pure functions have mature type/contracts after Hypothesis coverage | Symbolic search remains bounded and secondary. |
| Memray, pytest-leaks, or a psutil sentinel | A retained memory/reference leak reproducer exists | Native instrumentation and heavy artifacts are diagnostic, not a default pass/fail authority. |
| CodeQL | A major security audit requires provider-scale analysis | Heavy hosted/provider control plane. |
| OpenSSF Scorecard | Hosted repository posture needs observation | Provider observation is not local correctness proof. |
| ast-grep or LibCST | One-time structural search or repeatable Python codemod | Refactoring tools are not permanent policy; retained codemods need their own tests. |
| rumdl or typos | A replacement benchmark beats markdownlint/codespell with net deletion | Challenger tools cannot coexist permanently with the current owners. |
| yamlfmt | Human-owned YAML format drift becomes material | Most YAML is provider/OpenSpec projection already governed by owners. |
| Renovate | Dual-forge update policy, validation, and merge authority are designed | It must be the only update bot; Dependabot cannot coexist. |
| TruffleHog | Incident response needs verified-history diagnostics | Network verification and a second secret baseline do not belong in default proof. |
| OSV-Scanner | One scanner can replace uv/npm/artifact clients with less code | Current adoption would add binary supply and another wrapper without net deletion. |
| GuardDog | A new direct dependency or incident needs malicious-package analysis | Heuristic and network-bound supply analysis cannot become routine lockfile proof. |
| json-schema-diff | Public schema compatibility direction and supported schema set are declared | Current Draft 2020-12 contracts exceed the tool's reliable compatibility coverage. |
| SARIF tooling | More than one admitted producer needs one external interchange | ETHOS evidence remains typed repository truth; a format adapter must delete bespoke parsers. |
| MCP Inspector | Interactive MCP diagnosis is needed | The official conformance suite, not an interactive proxy/UI, owns automation. |
| Hosted AI reviewers | A human requests advisory review over non-sensitive code | Non-deterministic vendor findings never become a gate or claim authority. |
| sbomqs | A standard SBOM exists and a concrete field defect escapes SPDX validation | Aggregated quality scores must not become a parallel release authority. |
| Spectral | OpenAPI or AsyncAPI enters the repository | There is no API-description carrier today. |
| diffoscope | Two clean builds produce different hashes | Failure diagnosis only. |
| `git fsck --strict` or git-sizer | Object integrity or repository-history growth becomes an observed risk | Native/diagnostic repository health is separate from source correctness and must not become a parallel quality_summary. |
| LikeC4, CUE, TLA+, or Apalache | Model/query or state-space scale proves current declarations and Hypothesis insufficient | A second modeling or proof language needs a bounded invariant and deletion payoff. |
| Copier or Cruft | Multiple adopters share an updateable scaffold contract | Scaffolding cannot become a parallel source of repository truth. |
| Nox, Pixi, Pants | An adopter profile proves a bounded need | Optional adapters, never ETHOS core runtime. |

### Rejected defaults

- Pylint, Flake8, Black, isort, Radon/Xenon, refurb, slotscheck, interrogate,
  and a second permanent type checker duplicate Ruff, ty, or ETHOS-native gates.
- Vulture, slopo, and redup failed the signal, determinism, Python-compatibility,
  supply, or maintenance bar for this repository.
- SonarQube/SonarCloud, Snyk, DeepSource, Code Climate, Trivy omnibus,
  MegaLinter, Super-Linter, and Trunk create hosted or heavyweight parallel
  control planes.
- Mise, Devbox, Nix/devenv, and Pixi task/environment ownership are too broad for
  the core supply problem; Aqua is admissible only as the narrow CI binary adapter.
- Allure, pytest-rerunfailures, generic snapshot-approval plugins, pyperf beside
  pytest-benchmark, icontract/deal beside Pydantic/Hypothesis, and Schemathesis
  without an API schema add overlapping semantics or hide invalid states.
- mdformat, Prettier, dprint, and Biome conflict with carrier-native format
  owners; EditorConfig may guide editors but cannot become a second blank-line
  or formatting authority.
- Hadolint/Dockle, TFLint/Checkov, kubeconform/kube-linter, SQLFluff,
  Spectral/Schemathesis, Biome/Knip, notebook/data-quality, frontend accessibility,
  and LLM-evaluation stacks get no config while those asset classes are absent.
- pre-commit.ci, Dependabot beside Renovate, release-please, semantic-release,
  Commitizen, and Towncrier as a second release authority are rejected.

### Convergence order

1. Make catalog, owner scripts, descriptors, proof sets, and execution planes
   tell one exact story; narrow claims before adding tools.
2. Compile execution planes from the gate registry and replace repeated CI
   download logic with one narrow supply declaration; ban `latest` and ambient
   versions without introducing a second task/environment plane.
3. Partition docs into current/canonical, active-change, and immutable-history
   scopes; govern format, lint, type, and coverage suppressions as debt, not
   escape hatches.
4. Run P0 pilots, land only net-deleting or high-severity corrections, and
   retire losers immediately.
5. Bind replayable test receipts, then expand stateful, fault-injection,
   operation-history, time-boundary, metamorphic, concurrency, and mutation
   proof so stronger tests replace combinatorial examples; then add random-order
   and leak checks.
6. Prove Python 3.12/3.13/3.14 compatibility through one owner-script matrix.
7. Converge package and release quality in order: metadata, contents,
   reproducibility, SBOM generation, SBOM validation, licensing, artifact
   vulnerability, provenance, signing, and publication.
8. Keep local proof, emulator output, hosted observation, release evidence, and
   publication as separate claims throughout.

## Admission Contract

A planned tool becomes active only when one bounded Change supplies all of:

1. one capability owner and the alternatives it displaces;
1. pinned source, version, license, digest, cache, network, and write policy;
1. native config under the smallest stable owner;
1. one reusable owner script or `ethos ...` command;
1. descriptor/proof/execution-plane projections without copied command bodies;
1. deterministic output and two independent real findings or measurable net
   deletion; and
1. a terminal promote, absorb-and-retire, or reject decision.

Until then the mechanism stays roadmap-only and MUST NOT be reported as an
active quality floor.
