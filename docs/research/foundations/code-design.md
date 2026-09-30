---
subject: ethos:foundations-code-design
role: research
state: active
relations:
  part_of: ../modern-engineering-foundations.md
  informs: ../../plans/terminal-governance-product-design/implementation.md
  constrained_by: ../../governance/product-design-contract.md
---

# Code Design And Implementation

Purpose: select code-level designs that remove unnecessary states, decisions,
conversions and work across ETHOS product code, tests and tooling.

This study informs the [implementation strategy](../../plans/terminal-governance-product-design/implementation.md).
The [canonical plan](../../plans/terminal-governance-product-design.md) owns order;
official Changes own execution. Findings here are not a claim of completed repair.
Use [Foundation Topics](README.md) to move between code design, semantic analysis,
execution, verification and interfaces without returning to the full study.

## Choose A Reader Question

| Question                                                     | Read                                                            |
| ------------------------------------------------------------ | --------------------------------------------------------------- |
| What is wrong with widespread dictionaries?                  | [Data representation](#data-representation)                     |
| Where do design patterns actually fit?                       | [Implementation choices](#implementation-choices)               |
| What concrete code should change first?                      | [Observed implementation cuts](#observed-implementation-cuts)   |
| Where does native specialization violate product generality? | [Global product boundary audit](#global-product-boundary-audit) |
| Why did the first semantic-analysis draft fail?              | [Design comparison](#design-comparison)                         |
| How is a cleaner implementation accepted?                    | [Acceptance](#acceptance)                                       |
| Which original sources support these choices?                | [Sources and limits](#sources-and-limits)                       |

## Evidence Boundary

Observed on 2026-09-30 at accepted source
`ebe828d31aacca56f82b9a1dabc77e829989c328`, tree
`6a01425c21d3da7f1d127e5baeca25f56a11d722`.

The tracked Python inventory contains 311 product, 260 test and 37 tooling files.
AST inspection located broad mapping annotations, positional return tuples,
reflective access, serialization and diagnostic-text branching. These are
navigation signals. An occurrence is not automatically a defect.

The following mechanisms were inspected through their definitions and consumers:

- [Patch admission](../../../src/ethos/adapters/admission/patch_admission.py)
  passes six different observations positionally to a single caller.
- [Proof preparation](../../../src/ethos/adapters/mutation/proof.py)
  returns nine positional values, including several indistinguishable strings.
- [Result decoding](../../../src/ethos/result.py) serializes a Python mapping
  before strict JSON validation. Removing that round trip needs compatibility
  evidence because Pydantic's Python and JSON validation modes differ.
- [Current authority](../../../src/ethos/adapters/admission/current/authority.py)
  and [patch recovery](../../../src/ethos/adapters/admission/patch_admission.py)
  choose behavior from diagnostic string prefixes.
- [Proof CLI](../../../src/ethos/surface/cli/root/proof.py) reads a declared option
  with `getattr` and still performs application composition.
- [JSON value annotations](../../../src/ethos/contracts/value.py) enforce a value
  grammar at runtime but expose `Any` to static consumers.

Existing good foundations also matter: strict profile models, immutable plan
contracts, native Git object batching, invocation-scoped context, ParamSpec-based
application decorators and a shared gate executor already exist. Improve or reuse
them before adding an equivalent abstraction.

## Data Representation

Related question: [what syntax and binding analysis can establish](semantics.md#program-meaning-is-not-spelling).

The problem is loss of meaning in data, not the `dict` container itself.
A dictionary of file paths to bytes is a collection. A dictionary whose keys
must be exactly `head`, `tree`, `verdict` and `reason` is an implicit record.

| Data role                                         | Preferred representation                                                              | Why and limits                                                                                                                           |
| ------------------------------------------------- | ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Homogeneous lookup or index                       | `dict[K, V]`; `Mapping[K, V]` for read-only consumers                                 | Keys are data. Do not create a class per mapping entry.                                                                                  |
| Fixed internal observation                        | A named immutable record, normally `dataclass(frozen=True, slots=True, kw_only=True)` | Fields reveal meaning; keyword construction prevents positional swaps. It supplies no automatic runtime validation or deep immutability. |
| External configuration, receipt or protocol input | Existing strict Pydantic model                                                        | Parse once at the boundary; reject malformed fields and preserve the validated type. Generate external schema from its owner.            |
| Fixed JSON shape that must remain a dictionary    | `TypedDict`, optionally tagged with a literal                                         | Adds static structure without runtime conversion. It does not validate untrusted input.                                                  |
| Mutually exclusive states                         | Tagged union of small records; `match` and `assert_never` where exhaustive            | Model the permitted alternatives instead of independent flags and optional fields.                                                       |
| Static identity distinction                       | `NewType` when compile-time separation is sufficient                                  | Prevent commit/tree or resource/receipt mixing; runtime validation still belongs at input parsing.                                       |
| Behavioral substitution                           | A small `Protocol` or typed callable                                                  | Describes behavior, not a data container or a dependency-injection framework.                                                            |

### Preserve Meaning Across The Boundary

```text
untrusted bytes / mappings
        │ parse and validate once
        ▼
typed configuration or request
        │ pure interpretation and decisions
        ▼
named domain observations / permitted state alternatives
        │ serialize at an actual external boundary
        ▼
CLI JSON · MCP schema · receipt · persisted artifact
```

The same validated model may serve both transport and domain needs when their
meaning coincides. Do not manufacture DTO/domain/entity triplets by convention.
Convert only where lifetime, trust, mutability or public compatibility differs.

For example, patch observations are a product type: references, gaps, effects
and output identities can all exist together. Their fields belong in one record.
Execution states are a sum type: confirmed completion and unresolved outcome
have different required evidence and should not be interchangeable flag mixtures.

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class ConfirmedEffect:
    receipt_id: str
    observed_head: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UnresolvedEffect:
    attempt_id: str
    observation_gap: str


type EffectObservation = ConfirmedEffect | UnresolvedEffect
```

This illustrates a design choice; it is not a proposal for a second effect model.
Refine the existing owner's result when the distinction is actually missing.

### Avoid Replacement Traps

- Renaming `dict[str, object]` to `Payload` does not strengthen its contract.
- `frozen=True` prevents field reassignment, not mutation of a nested list/dict.
- `MappingProxyType` is shallow and can expose changes to its original mapping;
  privately build or copy the underlying data before publishing the view.
- `TypedDict` and Python annotations require a checker; they are not runtime guards.
- A generic `Result[T, E]` or monadic library is not automatically better than
  the existing closed verdict model and domain-specific results.
- A data class earns its cost only when it eliminates caller knowledge, ambiguity
  or repeated checks. Do not create one for every temporary pair.

## Implementation Choices

Companion studies cover [resource lifetimes](effects.md),
[execution and reuse](execution.md) and [replaceable interfaces](interfaces.md).

The relevant ideas span data-oriented, functional and object-oriented design.
Select the smallest design matching the actual variability and invariants.

### Data And Decisions

| Technique                        | ETHOS landing point                                                            | Use when                                                          | Do not use when                                                                            |
| -------------------------------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Parse, don't validate            | Profile loading, OpenSpec response parsing, proof receipts, patch observations | A check currently discards knowledge and callers check it again.  | A fresh external fact must be reobserved at effect time.                                   |
| Algebraic data types / typestate | Admission, pending effects, publication outcomes, runtime activation           | Distinct states require distinct fields and operations.           | A union or class would merely rename one scalar. Static type state cannot grant authority. |
| Declarative decision tables      | Rule applicability, closed command behavior, format selection                  | Branches encode data with one evaluation algorithm.               | The table hides distinct effects or becomes an undocumented mini-language.                 |
| Exhaustive pattern matching      | Closed verdicts, typed effects, expression syntax                              | Alternatives are finite and the checker can expose missing cases. | A fallback silently swallows new or unsupported states.                                    |

### Modules And Effects

| Technique                                 | ETHOS landing point                                                           | Use when                                                            | Do not use when                                                                     |
| ----------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Functional core, imperative shell         | `domain/*`, policy compilation, effect admission                              | A decision can be computed from explicit immutable observations.    | The fact is mutable or authority-sensitive and needs a fresh native read.           |
| Information hiding / deep modules         | OpenSpec lifecycle, source observations, artifact custody, runtime activation | Several callers know the same internal algorithm or ordering.       | Splitting a function just to reduce its line count adds forwarding layers.          |
| Strategy by composition                   | Gate providers, Forge effects, platform process handling, generators          | Two real implementations share a behavioral contract.               | A function argument suffices or only speculative variants exist.                    |
| Dependency inversion                      | Clock, Git/process execution, native observations                             | Passing a dependency isolates a real effect and simplifies testing. | A container, registry or factory only forwards a single dependency.                 |
| Context managers / structured concurrency | Locks, temporary roots, subprocess groups, MCP cancellation                   | Resources have lexical lifetime and bounded cleanup.                | A context manager is claimed to provide crash recovery or cross-resource atomicity. |
| Command/query separation                  | CLI/SDK/MCP preview and apply                                                 | Read-only inspection and admitted effects have different contracts. | CQRS databases or event sourcing would duplicate Git and Attestations.              |

### Shared Work And Verification

| Technique                                   | ETHOS landing point                                                | Use when                                                                    | Do not use when                                                                        |
| ------------------------------------------- | ------------------------------------------------------------------ | --------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Batching / common-subexpression elimination | Git objects, official OpenSpec reads, schema/reference analysis    | Multiple consumers need the same exact input observation.                   | Mutable state changes between reads or batching changes failure semantics.             |
| Memoization / incremental dataflow          | Pure parsing, compilation, dependency-complete checks              | Keys cover all relevant inputs and invalidation is demonstrable.            | Authorization, liveness, external freshness or effect outcomes are cached as truth.    |
| Single-flight work sharing                  | Same immutable supply or analysis requested concurrently           | Duplicate preparation is measured; one owner can publish a complete result. | An ordinary cache is sufficient or callers require independent execution.              |
| Property / metamorphic / stateful testing   | Alias invariance, rule conjunction, recovery, cooperation/all-drop | Laws and operation traces expose more mistakes than copied examples.        | Generated examples lack an independent oracle or replace necessary native fault tests. |

### Simpler Code Is Not Always Shorter Code

Replace deeply nested conditional expressions with a few named decisions when
that exposes precedence. Preserve one expression for a genuinely simple choice.
Do not use `match`, comprehensions, decorators or inheritance for ornament.

Prefer plain functions for stateless transformations. Use a class for an invariant,
resource lifetime or cohesive state. Prefer composition to base classes that make
execution order implicit. Native framework visitor method names are legitimate
protocol requirements; suppressions must not conceal arbitrary naming debt.

Keep data layout and algorithm together when they share a reason to change.
Read-only views, iterators and batching may avoid copies, but measure the cost of
generator layers and repeated traversals. Do not trade clear finite loops for
hard-to-debug chains or clever dynamic dispatch.

## Observed Implementation Cuts

| Owner                                | Current friction                                                                | Candidate change                                                                                         | Discriminating evidence                                                                                          |
| ------------------------------------ | ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Patch admission                      | Six-value positional result; fixed-shape patch dictionaries                     | Named observation, then typed patch variants if needed; mapping collections remain mappings.             | Same public verdict, paths, effects, profile identity and failure behavior; type checker catches swapped fields. |
| Proof preparation and issuing        | Nine-value return and broad check payloads                                      | One coherent proof-input value, typed check observations shared with the executor.                       | Exact evidence identity and missing/contradictory check refusal; fewer conversions and repeated checks.          |
| Current resolution and recovery      | Diagnostic prefix parsing and independently recomposed actions                  | Typed issue details and one continuation selection; render stable strings at the boundary.               | Change wording without changing recovery; malformed native output remains adverse.                               |
| Result/value contracts               | JSON round trip, static `Any` despite runtime grammar                           | Audit validation-mode semantics; narrow JSON recursively and expose typed data in fixed command results. | Existing strictness and wire schema preserved; unsupported values rejected; measured conversion reduction.       |
| OpenSpec lifecycle                   | Wide response dictionaries and repeated extraction                              | Parse official responses once; a typed observed lifecycle feeds status, proof and prewrite.              | Renamed/optional artifact, removal-only and archive behavior; source identity and UNKNOWN propagation.           |
| Proof CLI and installed interfaces   | Business composition remains in presentation; reflective reads of known options | Move complete operations to existing application owners; direct typed access to known fields.            | CLI/SDK/MCP conformance and no presentation-dependent policy.                                                    |
| Process/resource handling            | Repeated startup, cleanup and failure translation                               | One lexical owner plus bounded native recovery; pass explicit execution dependencies.                    | Real cancellation, lost supervisor, stderr preservation and no duplicate destructive retry.                      |
| Test fixture and native verification | Large setup for pure decisions; provider repeats executed suites                | Pure core tests plus real effect tests; share immutable preparation and native result material.          | Same cases and coverage, changed-input rejection, lower setup/body/cleanup cost.                                 |

These are coordinated cuts, not a request to rename all packages at once.
Their execution order remains in the existing [implementation strategy](../../plans/terminal-governance-product-design/implementation.md).

## Design Comparison

The first local LibCST draft combined symbols, strings, commands and an unknown
flag in one bag, then approximated reaching definitions by source position and
ancestor sets. It was not connected to production consumers.

Executed falsifiers showed why that design was rejected:

1. A conditional assignment was reported complete even when the variable could
   remain unbound.
2. `subprocess.run('tool with spaces', shell=False)` was split into shell tokens,
   inventing a different executable.
3. A known subprocess target combined with an unknown target lost its uncertainty.
4. An aliased dynamic lookup was not recognized as unresolved.

That draft was removed. The obligation remains open; source-level progress and
remaining limitations are separated in the comparison below.

| Design                                                            | Benefit                                                        | Cost / verdict                                                                                            |
| ----------------------------------------------------------------- | -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Extend spelling heuristics                                        | Low immediate code churn                                       | Cannot establish binding or flow; reject.                                                                 |
| Library binding plus explicit bounded value/control-flow analysis | Precise ownership, useful partial knowledge and scoped UNKNOWN | Must handle joins, unbound values and call semantics; qualify before runtime adoption.                    |
| External full analyzer                                            | May provide richer flow facts                                  | Language/version, packaging, startup, licensing and adaptation cost require a common-workload comparison. |

LibCST's scope metadata does not itself prove effect semantics. Avoid installing
an analysis platform merely to replace one incomplete interpreter with another.

### Scoped Inference Comparison

On 2026-09-30 the candidate replaced whole-tree constant selection and owner-name
matching with Python's compiler symbol tables, typed alternative values and
native `singledispatchmethod` transfer rules. Imports, call targets, argument
vectors, shell programs and unresolved alternatives remain distinct. The
[public regressions](../../../tests/unit/repository/policy/python/test_binding.py)
exercise aliases, lexical shadowing, program points, branch joins, late binding,
comprehensions, exception targets, member replacement and shell/executable modes.

The initial 27-case green was insufficient: eight additional cases failed.
Those are now retained and pass with the repaired candidate; 119 adjacent cases
pass. One old fixture supplied a spelling `subprocess` without importing it;
adding its missing import preserved the intended assertion rather than restoring
the spelling heuristic. Ruff and Ty pass for the changed semantic owner.

[Astroid 4.3.3 metadata](https://pypi.org/pypi/astroid/4.3.3/json) reports Python
3.10 or newer and LGPL-2.1-or-later. Its [inference documentation](https://pylint.readthedocs.io/projects/astroid/en/latest/inference.html)
explains alternatives and `Uninferable`; the retrieved documentation identified
itself as 4.4.0-dev0, not the tested stable release. A temporary, dependency-free
installation of 4.3.3 was tested against sources extracted from the same tests.
It resolved ordinary aliases and constants, but missed the local-before-assignment
distinction and an earlier possible global value. A member-assignment probe also
changed a later unrelated module's inferred `subprocess.run` candidates until
`MANAGER.clear_cache()` restored the cold result. These were inference observations;
the sample repository programs were not executed.

Decision: do not adopt Astroid as this trust-bearing resolver or add its runtime
dependency. Do not interpret these counterexamples as a verdict on its other uses.
Use compiler-native scope facts here; retain LibCST for a demonstrated syntax or
editing need rather than importing it as a completeness certificate.

The candidate is not qualified for acceptance. The original whole-repository
draft reported 33 unresolved consumer-kind/path pairs. The current public
`product-boundary` observation after commits `2d752e955` and `104f43886` reports
20 unresolved consumer-kind/path pairs and no orphan finding. Presence probes
do not require their targets; a fixed lookup result retains its program identity
only at an actual execution boundary. Shell array assignment and append retain
the same non-executing storage meaning.
Some are genuine dynamic boundaries; others expose overly broad uncertainty
from argument suffixes that cannot change the executable. Resolve only facts
needed by the claimed relation, preserve runtime capability obligations, and
distinguish partial interpretation from syntax failure. Do not whitelist these
paths, declare all generic dispatchers complete, or deploy permanent blocking as
a substitute for a usable model. Current evidence covers the named cases, not
arbitrary Python heap effects or whole-program behavioral equivalence.

## Acceptance

Use the [verification study](verification.md#executable-wiring-review) for the
distinction between declared checks, actual execution and sufficient evidence.

Every refactor must preserve required behavior and reduce at least one measured
cost: caller concepts, illegal state space, repeated decisions, conversions,
resource work, change coupling or verification effort.

- **Correctness:** reuse existing public regressions; add a counterexample for a
  newly discovered semantic gap. No tests that only restate the new class layout.
- **Structure:** all consumers use the one owner; remove old representations and
  conversion paths in the same cut. No compatibility facade without a consumer.
- **Types:** verify product, tooling and tests at their actual checking scope;
  introducing an annotation alone does not prove enforcement.
- **Performance:** compare identical workloads, including initialization and
  cleanup. Record uncertainty; a microbenchmark is not whole-proof performance.
- **Readability:** a reader can locate the invariant, effects, failure and caller
  obligations without tracing a chain of wrappers or consulting prior chat.

Use [quality and throughput tasks](../../../openspec/changes/proof-throughput/tasks.md)
9.9 for structural cuts, 10.11 for semantic observation, and 8.10 for complete
type/report coverage. This document adds no separate implementation queue.

## Global Product Boundary Audit

The September 30 inspection starts from the same accepted source above, with
uncommitted candidate repairs explicitly separate. Inventory covered 1,450
present tracked files, including 310 Python product carriers, 260 tests and 37
tools. Syntax comparisons and symbol references selected the semantic owners
below; inventory counts are not proof of exhaustive behavioral correctness.

| Responsibility and owner                                                                                                                                | Observation and disposition                                                                                                                                                                                                                    |
| ------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Product meaning](../../governance/product-design-contract.md) and [profile contract](../../governance/repository-profile-contract.md)                  | Preserve language-neutral obligations and repository-native commands. Neither a universal Python layout nor a named adopter belongs in the product ontology.                                                                                   |
| [Gate descriptor](../../../src/ethos/contracts/gates.py)                                                                                                | Preserve generic execution and resource semantics. Built-in provider references remain product-owned; an external trusted capability admission contract is still required, not an unrestricted import hook.                                    |
| [Policy compiler](../../../src/ethos/repository/policy/gates.py)                                                                                        | Preserve exact-tree, exact-set conjunction across several checks. Current inline profiles already derive execution transport; do not repeat the old-runtime metadata repair.                                                                   |
| [Carrier observation](../../../src/ethos/adapters/repo/gate_policy.py) and [role interpretation](../../../src/ethos/repository/policy/code_subjects.py) | Repair explicit code/tooling roles overridden by test-like paths, and failed Git inventory mistaken for an empty scope. Unknown-language declared code must retain obligations.                                                                |
| [Native verification](../../../src/ethos/adapters/gates/code_quality.py)                                                                                | Replace all-language dispatch, implicit all-tests selection and duplicate native runs with admitted scope/input-qualified evidence. Current Go execution, Node exact-argv matching and Python refusal do not implement that terminal contract. |
| [Python verifier](../../../src/ethos/adapters/gates/python_quality.py)                                                                                  | Native Ruff/pytest adapters are legitimate; forcing their isolated policy and discovery onto every Python adopter is not. Preserve native configuration, selection and same-attempt reports.                                                   |
| [Native report interpretation](../../../src/ethos/repository/policy/quality_reports.py)                                                                 | JUnit, Cobertura, LCOV and Go event semantics require format adapters, not per-language governance. Move format interpretation out of policy with all consumers when that boundary closes; a cosmetic rename is insufficient.                  |
| [Reference observation](../../../src/ethos/repository/policy/references/observation.py)                                                                 | Parsers legitimately differ by carrier. Syntax success cannot certify semantic closure; unresolved dynamic meaning remains scoped unknown. The Python resolver repair is not universal language support.                                       |
| [Formation](../../../src/ethos/adapters/repo/starter/generation.py)                                                                                     | Keep optional native generators and foundation preservation. A foundation plus one Python starter is not general domain-scaffold completion; fallback selection and generator-specific checks need the existing capability contract.           |
| [Rules](../../../src/ethos/repository/policy/rules/compile.py), [layout](../../../src/ethos/repository/policy/layout/policy.py) and docstring checks    | Separate optional Python/self-host checks from universal obligations. The broad import-layer contract alone does not enforce this applicability distinction.                                                                                   |
| [Skill capabilities](../../../src/ethos/assistants/skills/capabilities.py)                                                                              | Interpreter-name prefix rejection and bundled-script membership are not a general effect model. Preserve admission while qualifying replaceable capability identity, permissions and effects.                                                  |
| [Runtime binding](../../../src/ethos/adapters/repo/runtime/binding.py) and CI supply                                                                    | Python implementation and platform-specific packaging do not require adopters to use Python. Preserve package compatibility without projecting implementation language into repository rules.                                                  |
| [Tests](../../../tests/unit/adoption/quality/test_code.py) and [native report cases](../../../tests/unit/adoption/quality/test_go.py)                   | Preserve real native regressions. Classify tests by the contract they prove; deleting Go cases would remove evidence without fixing language dispatch.                                                                                         |

The role counterexample reproduced at the public policy compiler with native
Git attributes across Python, Go, JavaScript and two unqualified carrier forms.
Declared code under `tests/` had disappeared from behavior obligations. The
candidate gives explicit code/test/tooling roles precedence without allowing a
non-code label to erase recognized code. A corrupted-index counterexample now
refuses unavailable discovery rather than compiling an empty scope. The 25-case
policy suite passes; this is not full proof or installed-product delivery.

The [existing implementation strategy](../../plans/terminal-governance-product-design/implementation.md)
owns convergence. Official `proof-throughput` tasks 11.9.1/11.9.2 retain native
scope, same-attempt evidence, prior-policy preservation and adopter acceptance.
No second language registry, plugin platform or task ledger is introduced.

## Sources And Limits

Read on 2026-09-30 through Agent Reach's Exa search/fetch route. These are original
author or official sources; age alone does not invalidate an enduring design idea.
The excerpts support design principles, not proof of ETHOS implementation quality.

| Source                                                                                                                                                     | Applied lesson                                                                                                                                                   |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Alexis King: Parse, don't validate](https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/)                                                  | Retain facts learned by parsing in types rather than discard them and recheck.                                                                                   |
| [Scott Wlaschin: Make illegal states unrepresentable](https://fsharpforfunandprofit.com/posts/designing-with-types-making-illegal-states-unrepresentable/) | Model allowed alternatives explicitly; optional fields can admit impossible states.                                                                              |
| [John Ousterhout: A Philosophy of Software Design](https://web.stanford.edu/~ouster/cgi-bin/book.php)                                                      | General-purpose modules and deciding what matters; the author explicitly differs from mechanical small-method rules. The book page, not its full text, was read. |
| [Gary Bernhardt: Boundaries](https://www.destroyallsoftware.com/talks/boundaries)                                                                          | Simple values at boundaries and isolation of effects. Only the original talk description was read, not the video.                                                |
| [Martin Fowler: Presentation Domain Data Layering](https://martinfowler.com/bliki/PresentationDomainDataLayering.html)                                     | Separate reasons to change while iterating across layers.                                                                                                        |
| [Refactoring: Replace Conditional with Polymorphism](https://refactoring.com/catalog/replaceConditionalWithPolymorphism.html)                              | Move behavior with genuinely varying alternatives; do not introduce classes for every conditional.                                                               |
| [Python 3.12 typing](https://docs.python.org/3.12/library/typing.html)                                                                                     | Type aliases, NewType and Protocol have different guarantees; annotations are not runtime checks.                                                                |
| [Python contextlib](https://docs.python.org/3.12/library/contextlib.html)                                                                                  | Lexical cleanup and correct exception propagation; no implied crash atomicity.                                                                                   |
| [Python functools](https://docs.python.org/3.12/library/functools.html)                                                                                    | Cache coherence does not prevent concurrent duplicate computation; cached properties are not universal immutable storage.                                        |
| [AnyIO cancellation](https://anyio.readthedocs.io/en/stable/cancellation.html)                                                                             | Task-group cancellation, bounded shielding and re-raising cancellation; account for level-cancellation semantics.                                                |
| [Hyrum's Law](https://www.hyrumslaw.com/)                                                                                                                  | Observable behavior can become a consumer dependency; verify real callers before removing accidental interfaces.                                                 |

A Parnas PDF fetch failed and is not cited as inspected evidence. Retrieved pages
were excerpt-bounded. No claim of exhaustive literature coverage or global optimality
follows. Further tool choices use the [foundation comparisons](README.md).
