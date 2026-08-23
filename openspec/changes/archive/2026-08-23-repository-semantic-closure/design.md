## Context

`repository_audit()` is the existing aggregate owner, but today it combines
several open dictionaries and set-based scans. `repository_product_reference_gaps()`
can prove only that a consumed identity appears in an allowed set. It cannot
prove that the identity has exactly one owner, that the owner is current, or
that every required producer/consumer/selector edge exists. Separately,
`design_integrity_report()` explicitly projects `semantic_equivalence` as
`not_evaluated` while still allowing the aggregate audit to pass.

## Goals / Non-Goals

**Goals:**

- Derive global closure from current Git-tracked native carriers at audit time.
- Retain exact path and relation provenance until validation is complete.
- Report one closed vocabulary: missing, duplicate, orphan, superseded,
  conflict, and unknown.
- Make `repository_audit()` the single public owner of the aggregate verdict.
- Delete or demote overlapping partial reports to typed observations.

**Non-Goals:**

- Persisting an index, graph, cache, ledger, or workflow state.
- Inferring relations from unstructured prose, archived Changes, evidence, or
  examples; declared Markdown and OpenSpec structure remains machine input.
- Letting audit, documentation, or a generated projection authorize effects.
- Expanding this atom into evidence-retention, runtime, adoption, or lifecycle
  repair.

## Decisions

### Closure is a finite relation over observed current carriers

The audit compiler reads the same tracked current carrier set already used by
repository policy. Native declarations produce owner facts; references produce
consumer facts; declaration tables and command attachment points produce
selector facts. Evaluation occurs in memory and the relation is discarded
after projection. No durable graph is introduced.

Alternative rejected: add a semantic registry. A second registry would become
another truth store and would drift from the native declarations it attempts to
describe.

### Provenance precedes set reduction

The existing admitted-reference sets remain useful to patch admission, but the
repository audit must evaluate path-qualified facts before reducing identities
to sets. Exactly one current owner is required for each governed identity;
zero, several, superseded-only, or contradictory owners are distinct failures.

Alternative rejected: scan for forbidden strings. Negative lists cannot prove
coverage and misclassify historical or test examples.

### One typed closure projects all categories

The closure result owns the category vocabulary and deterministic ordering.
`repository_audit()` consumes it and derives its verdict and gaps. Design and
reference helpers return observations used by that result rather than parallel
aggregate verdicts. This keeps the semantic owner singular without making the
large repository audit function own parsing details.

### Currentness is structural

Only current tracked product surfaces, accepted OpenSpec specs, active Change
material, rules, system declarations, source, tests, and fixtures selected by
their native carrier participate. Archived Changes, evidence, generated output,
and explicitly superseded documentation remain historical context, not owners.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| `assistant-projections:*` | `2.4` | current assistant projection ownership is either retained once or deleted from the accepted spec; repository closure reports no duplicate or orphan relation |
| `command-plane:*` | `2.4` | current command identities and lifecycle projections are retained once or deleted from the accepted spec; command-owner and consumer closure is zero-gap |
| `contracts:*` | `2.4` | current contract ownership is retained once or deleted from the accepted spec; repository closure reports no duplicate owner |
| `proof-hosts:*` | `2.4` | retired proof-host projection semantics are absent from current ownership while historical carriers remain non-authorizing |
| `quality:*` | `2.2` | duplicate-owner, orphan-relation, historical-carrier, prohibition-example, and parse-failure RED/GREEN tests exercise the closed category vocabulary |
| `repository-governance:*` | `2.4` | current repository-governance ownership is retained once or deleted from the accepted spec; aggregate repository audit reports zero gaps |

## Risks / Trade-offs

- [Risk] Provenance scanning increases audit latency -> parse each selected
  carrier once and benchmark the focused gate before full proof.
- [Risk] Historical prose is classified as current -> use structural carrier
  selection and maturity metadata, never literal allowlists.
- [Risk] A new report duplicates an incumbent -> replace the aggregate
  `reference_ownership` and unevaluated design projection rather than retaining
  both.
- [Risk] Categories are broader than mechanically known facts -> emit `unknown`
  and fail closed instead of guessing.

## Migration Plan

1. Add real false-positive tests against current audit composition.
2. Introduce provenance-preserving observations behind the existing reference
   policy package.
3. Compile and project one typed closure from `repository_audit()`.
4. Delete superseded set-only aggregate/report fields and migrate callers.
5. Repair current repository gaps, prove strict OpenSpec and focused gates, then
   run the complete lifecycle closeout.
