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

## Sources

Links identify inspected documents, not blanket endorsements. Source-level and
README observations above have different strength; repository popularity and
marketing claims were not used as evidence of comparative performance.

[cue]: https://github.com/cue-lang/cue/blob/e83d953917a564d12cf9a1cfcac5ecca9e8a711a/README.md
[cue-json-schema]: https://cuelang.org/docs/concept/how-cue-works-with-json-schema/
[json-numeric]: https://json-schema.org/understanding-json-schema/reference/numeric
[cel]: https://github.com/google/cel-spec/blob/ba58ae5007845f3a1279b488cdeb79645ce958bb/README.md
[jsonschema]: https://github.com/json-schema-org/json-schema-spec/blob/4f56a9900674b27804f0ec32e3b7fdfa4efad695/README.md
[cedar]: https://github.com/cedar-policy/cedar/blob/2f4019fd645cc8d4a4c0c1f8bd0280c77d754e28/README.md
[cel-verifier]: https://github.com/cel-expr/cel-java/blob/33da350d02e2b14bc76f622fca2b9687c90c509a/verifier/README.md
[quint]: https://github.com/informalsystems/quint/blob/6fb2924e00707cef6dbc5e30db606d555c447123/README.md
[libcst-mechanism]: https://github.com/Instagram/LibCST/blob/d9a255843b5cdbecc6834684d233bce1f2987f9d/libcst/metadata/scope_provider.py
[tree-sitter]: https://github.com/tree-sitter/tree-sitter/blob/b2cf42f7ef45bbcbd527a4ea8ffdb9cc7b2b3500/README.md
[lsp]: https://github.com/microsoft/language-server-protocol/blob/3d9ba5d8e28ab7a577bb5aed1f27c166da0cb558/_specifications/lsp/3.17/specification.md
[scip]: https://github.com/sourcegraph/scip/blob/a279febaad96d05c8bc303c1bcaa11ebf348a82b/README.md
[codeql]: https://github.com/github/codeql/blob/cfc358e846dc1b26f4be2d1d2854c0d983c12ce8/README.md
[networkx]: https://github.com/networkx/networkx/blob/4e74880b0da01977da79915167c64e5c2af38b47/README.rst
