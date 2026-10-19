---
subject: ethos:foundations-semantics
role: research
state: active
relations:
  part_of: ../modern-engineering-foundations.md
  informs: ../../plans/terminal-governance-product-design.md
  constrained_by: ../../governance/product-design-contract.md
---

# Executable Constraints And Program Semantics

Status: active research; dated observations retain their original evidence limits.

Purpose: Distinguish declarative validation, name binding, flow and proof obligations.

See also: [Research Overview](../modern-engineering-foundations.md),
[Product Design Contract](../../governance/product-design-contract.md), and
[Terminal Plan](../../plans/terminal-governance-product-design.md).

## Declarative Constraints And Semantic Analysis

[CUE][cue] is a serious candidate to consolidate configuration composition and
validation. [CEL][cel] is a serious candidate for bounded pure policy predicates;
it is already a declared ETHOS dependency, not an entirely absent capability.
[JSON Schema][jsonschema] remains an interoperability option for wire structures.
These serve different layers, but overlapping manually maintained definitions do
not become legitimate merely because each is in a different language.

Trial one real duplicated rule family: choose one editable declaration owner,
derive all necessary projections, reject contradictions before execution, and
compare canonical meaning and error paths. Remove superseded validators and
schemas in the same migration. CUE unification does not understand user intent;
CEL parsing does not imply static type checking, boolean result correctness or
bounded evaluation in the selected implementation. A dynamically typed context
can defer misspellings until runtime. Candidate policy cannot weaken its trusted
predecessor to approve itself.

[Cedar][cedar] is worth comparison if entity/relationship authorization becomes
the specific duplication to remove. It is not a second general policy language
to add alongside CEL without an ownership partition. [CEL's Java verifier][cel-verifier]
and [Quint][quint] offer useful bounded reasoning experiments. The inspected CEL
verifier leaves some functions uninterpreted and bounds dynamic comprehensions;
UNKNOWN outside its supported proof boundary is not a universal theorem.

Use the smallest formal model that can expose stale generation, duplicate effect,
missing success path, bad policy replacement or lifecycle cycles. Translate a
counterexample into a real public-entry regression. A proof about a model is not
an implementation proof without a checked correspondence and explicit assumptions.

### Executed CUE Rule Trial

On September 15, the accepted `c03e209118ba72120c58278996fab1a6043bc927`
source was compared with the already installed CUE 0.17.1 executable. No tool
installation, dependency change, adopter mutation or production CUE integration
occurred. The trial consumed the actual three rules in `.ethos/rules.toml`,
`system/schemas/kernel/rule.schema.json` and the installed strict `Rule` model.

Native `cue def jsonschema+strict:` imported that schema without a handwritten
CUE copy, using the [official JSON Schema integration][cue-json-schema]. Native
export exercised twelve cases: the three actual rules, missing
owner, empty paths, unknown field, invalid severity, Boolean/string/float version,
numeric owner and omitted default version. All three consumers agreed except
for `version: 1.0`: JSON Schema accepted it; the strict Python model and imported
CUE definition rejected it. JSON Schema [defines integral numeric values][json-numeric]
independently of decimal spelling. This is a real carrier/representation distinction,
not evidence that CUE has understood the policy or that every rule is equivalent.
Contradictory severity declarations were rejected in either input order.

Exporting the imported definition back to JSON Schema preserved verdicts across
these twelve cases. The selected CLI documents JSON Schema output as experimental;
this small round trip does not qualify every keyword, default, reference, error
path or supported platform. Both owned scratch directories were removed.

The demonstrated replacement opportunity is the manually repeated structural
rule contract, not another validator beside the current ones. CUE is a strong
candidate for composing declaration constraints and rejecting contradictions
before execution. For an already typed Python wire model, native schema generation
is a competing lower-cost replacement and must be compared rather than ignored.
Choose one editable owner per rule family; generated wire schemas and Python
values are projections, not independently editable policy. Settle the numeric
carrier distinction explicitly before switching any consumer.

The trial is recorded in the existing ignored quality evidence as
`build/evidence/quality/validation-results/cue-rule-evaluation.json`: exact source,
input and binary hashes,
argv, stdout/stderr, individual verdicts and cleanup readback. Production
packaging, offline supply, native-platform qualification, error compatibility
and measured cold/warm cost remain unproved. Prior research prioritized this
trial; it did not justify indefinite deferral or establish that CUE was already
an implemented profile compiler. CUE cannot replace fresh authorization,
effect observation, recovery or accepted OpenSpec intent.

### Program Meaning Is Not Spelling

The current `python_syntax.py` still constructs a whole-tree string table and
recognizes certain calls by owner spelling. Earlier independent public-gate
probes demonstrated alias, shadowing and program-point counterexamples. This
review re-observed the mechanism, but did not replay that public workload at the
current dirty source; it does not assert full proof or publication bypass.

[LibCST's scope implementation][libcst-mechanism] handles names, assignments and
access relationships. It is a candidate to replace spelling-based binding
heuristics, not a complete value-flow/effect interpreter. [Tree-sitter][tree-sitter]
is useful for incremental syntax, [LSP][lsp] for language-service capabilities,
and [SCIP][scip] for semantic indexing. The inspected LSP 3.17 document calls
itself a previous revision; it is not a current-version recommendation. Each
observation must carry its source,
provider, supported semantics and completeness boundary. No syntax tree or symbol
index automatically proves behavioral equivalence.

[CodeQL][codeql] is a stronger flow-analysis candidate for selected high-risk
questions, subject to execution, language support, licensing and maintenance
cost. [NetworkX][networkx] is a reusable graph algorithm library, not a reason to
persist a second semantic graph. Derive dependency, impact, reachability and
orphan views from owners. Structural isomorphism is a useful duplicate candidate
signal only when node/edge meaning, effects, assumptions and boundaries agree.

Move supported cases into the unique observation owner, delete substituted
heuristics, and test aliasing, alpha-renaming, local shadowing, reassignment,
conditional import, unresolved dynamic call and legitimate negative cases.
Unsupported dynamic behavior produces relevant UNKNOWN, not a global permanent
block. Code semantics must not narrow the full product chain.

### RepoWise: Navigation Without Imported Authority

Disposition: introduce the unmodified external tool for derived navigation and
reviewed quality leads. After successful consumer acceptance, promote it across
ETHOS and governed repositories through existing capability and adoption owners;
do not leave it permanently trial-only. It is not a product dependency, mandatory
score gate, intent owner, deletion authority or unqualified test selector.

The fixed October 4 trial used RepoWise 0.55.0, upstream
`e829775bfd18f22ff2f9522d514d3b94c1fde2b6`, against ETHOS source
`e34b3a286510d43eb622b401dbc3f228446c6509`. Its original fast run and completed
health run did not assess subsequent dirty candidate bytes.

| Capability               | Actual observation                                                                   | Limit                                                                                       |
| ------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| Index and symbol context | Init 34.083 seconds; queries 2–6 seconds                                             | Derived structural navigation, not behavior completeness                                    |
| Dead-code candidates     | Two exports received `safe_to_delete=true`                                           | Dynamic/external consumers remain unclosed; neither was deleted                             |
| Impacted tests           | 809 inferred entries, five unknown files, `run_all=true`                             | No coverage map or justified test reduction                                                 |
| Health                   | Completed in 44.842 seconds: 671 metric rows, 1,817 findings, 1,165 product findings | Supersedes the first 35-second timeout; coverage is null, findings are hypotheses           |
| Installed tool           | Official independent UV installation and structural index/query/update accepted      | Live project and Agent MCP rollout, model answers and byte-current health remain unaccepted |

#### Mechanism Decisions

| Mechanism                                                                      | Decision and reason                                                                                                                                                                                              |
| ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Graph construction][repowise-graph]                                           | Introduce derived symbol/import/call navigation. Explicit imports help; unique-name fallback and confidence filters do not prove runtime callees, ownership or absent consumers.                                 |
| [Parse reuse][repowise-parse-cache] and [edge persistence][repowise-persist]   | Borrow content-bound reuse and parser-fingerprint invalidation. A parser change widens reconciliation to unchanged files; a warm update still reads and resolves source. Watch alone does not prove freshness.   |
| [Batched context][repowise-context] and [index identity][repowise-index-state] | Borrow bounded owner/caller selection and reusable immutable computation. Bind project/store, source snapshot, analyzer and configuration; preserve omitted/unknown scope and never cache current authorization. |
| [I/O markers][repowise-io]                                                     | Adapt as performance leads, not redundant-work verdicts. They recognize sinks inside supported loop bodies, not repeated input identities or a measured execution cost.                                          |
| [Clone markers][repowise-dry]                                                  | Borrow refactoring candidates, not semantic equivalence. Cross-file token clones and co-change cannot establish shared responsibility; same-file clones are not this marker's scope.                             |
| [Primitive signatures][repowise-primitive]                                     | Borrow model-review leads. File size, parameter counts and lexical type names do not prove an absent domain model or require a dataclass.                                                                        |
| [Scoring][repowise-score]                                                      | Reject as acceptance or deletion authority. Ranking prioritizes investigation; a zero result can mean unsupported syntax or no extracted signal.                                                                 |

The October 5 native in-memory probe did not execute sample code or index a
Lane. The committed projection reader produced one I/O marker; the repaired
reader produced two, although equal observations required 227 versus 34 actual
text reads. Both unique and repeated `Path(...).read_text()` comprehension
samples produced no marker. Malformed syntax likewise produced no marker.
The direct `loop_key_unused` identifier-overlap test does not track a loop key
through a derived local. These observations reject score/count reduction as a
substitute for behavioral verification.

#### ETHOS Repair And Gate Coverage

The unique patch-admission observation owner now reads each effective projection
input at most once per invocation, then overlays exact postimages. Equal-result
fixtures measured 10→3 and 227→34 reads; shared source and declaration each
fell to one. No persistent cache or authority reuse was introduced. Public
admission retains regeneration, tamper, deletion, retirement and external-owner
refusal. Forty-seven final cases, native lint/format/type and module layout pass;
Allure 3 was generated from that same attempt without another test run. This is
candidate evidence, not an accepted or installed successor.

Native Ruff already enabled `PERF`, but the repeated-reader baseline passed:
those rules do not assert exact-input cardinality. The owner regression now
asserts that property. Separately, `max-args=7` was inert because `PLR0913` was
not selected. An eight-argument native probe passed active configuration and was
rejected when that rule was selected. Remove the misleading setting rather than
pretend a count alone proves good domain design. Explicit analysis identified
77 signatures for review, not 77 established model defects. Mechanical coverage,
semantic review and actual cost retain distinct acceptance predicates.

Keep the tool isolated: the trial resolved 135 packages and its MCP requirement
conflicts with ETHOS's floor. The official wheel is AGPL-3.0-or-later; external
unmodified use is distinct from code copying, library linkage or redistribution.
No integration-specific legal conclusion or reduced dependency closure is claimed.
Retain grammar/network and stdout-framing warnings. Do not run default editor,
hook, prompt or MCP bootstrap against a protected or active Lane.

Evidence remains in the existing custody: `repowise-trial-cu1e3d91/results/`
(first trial), `repowise-quality-completion-xql_swxp/results/` (completed health),
and `repowise-optimization-9wli7wjw/` (exact source bindings, native mechanism
probes, final matched reads, public RED/GREEN, Allure and owned cleanup).
The host installation receipt is
`repowise-official-installation-acceptance-20261005.json`, SHA-256
`39be6853501b3a42bee4e3e603b48e5f4c2db9d3358cef5f7a655141258c9314`.
Matched Agent quality, token savings, complete iteration speed, live watch and
fleet conformance remain unqualified; each affected owner keeps those obligations.

## Sources

Links identify inspected documents, not blanket endorsements. Source-level and
README observations above have different strength; repository popularity and
marketing claims were not used as evidence of comparative performance.

[cue]: https://github.com/cue-lang/cue/blob/e83d953917a564d12cf9a1cfcac5ecca9e8a711a/README.md
[cue-json-schema]: https://cuelang.org/docs/concept/how-cue-works-with-json-schema/
[json-numeric]: https://json-schema.org/understanding-json-schema/reference/numeric
[cel]: https://github.com/cel-expr/cel-spec/blob/ba58ae5007845f3a1279b488cdeb79645ce958bb/README.md
[jsonschema]: https://github.com/json-schema-org/json-schema-spec/blob/4f56a9900674b27804f0ec32e3b7fdfa4efad695/README.md
[cedar]: https://github.com/cedar-policy/cedar/blob/2f4019fd645cc8d4a4c0c1f8bd0280c77d754e28/README.md
[cel-verifier]: https://github.com/cel-expr/cel-java/blob/33da350d02e2b14bc76f622fca2b9687c90c509a/verifier/README.md
[quint]: https://github.com/quint-co/quint/blob/6fb2924e00707cef6dbc5e30db606d555c447123/README.md
[libcst-mechanism]: https://github.com/Instagram/LibCST/blob/d9a255843b5cdbecc6834684d233bce1f2987f9d/libcst/metadata/scope_provider.py
[tree-sitter]: https://github.com/tree-sitter/tree-sitter/blob/b2cf42f7ef45bbcbd527a4ea8ffdb9cc7b2b3500/README.md
[lsp]: https://github.com/microsoft/language-server-protocol/blob/3d9ba5d8e28ab7a577bb5aed1f27c166da0cb558/_specifications/lsp/3.17/specification.md
[scip]: https://github.com/scip-code/scip/blob/a279febaad96d05c8bc303c1bcaa11ebf348a82b/README.md
[codeql]: https://github.com/github/codeql/blob/cfc358e846dc1b26f4be2d1d2854c0d983c12ce8/README.md
[networkx]: https://github.com/networkx/networkx/blob/4e74880b0da01977da79915167c64e5c2af38b47/README.rst
[repowise-graph]: https://github.com/repowise-dev/repowise/blob/e829775bfd18f22ff2f9522d514d3b94c1fde2b6/packages/core/src/repowise/core/ingestion/graph/builder.py
[repowise-parse-cache]: https://github.com/repowise-dev/repowise/blob/e829775bfd18f22ff2f9522d514d3b94c1fde2b6/packages/core/src/repowise/core/ingestion/parse_cache.py
[repowise-persist]: https://github.com/repowise-dev/repowise/blob/e829775bfd18f22ff2f9522d514d3b94c1fde2b6/packages/core/src/repowise/core/pipeline/persist.py
[repowise-context]: https://github.com/repowise-dev/repowise/blob/e829775bfd18f22ff2f9522d514d3b94c1fde2b6/packages/server/src/repowise/server/mcp_server/tool_context/context.py
[repowise-index-state]: https://github.com/repowise-dev/repowise/blob/e829775bfd18f22ff2f9522d514d3b94c1fde2b6/packages/server/src/repowise/server/mcp_server/_index_state.py
[repowise-io]: https://github.com/repowise-dev/repowise/blob/e829775bfd18f22ff2f9522d514d3b94c1fde2b6/packages/core/src/repowise/core/analysis/health/biomarkers/io_in_loop.py
[repowise-dry]: https://github.com/repowise-dev/repowise/blob/e829775bfd18f22ff2f9522d514d3b94c1fde2b6/packages/core/src/repowise/core/analysis/health/biomarkers/dry_violation.py
[repowise-primitive]: https://github.com/repowise-dev/repowise/blob/e829775bfd18f22ff2f9522d514d3b94c1fde2b6/packages/core/src/repowise/core/analysis/health/biomarkers/primitive_obsession.py
[repowise-score]: https://github.com/repowise-dev/repowise/blob/e829775bfd18f22ff2f9522d514d3b94c1fde2b6/packages/core/src/repowise/core/analysis/health/scoring.py
