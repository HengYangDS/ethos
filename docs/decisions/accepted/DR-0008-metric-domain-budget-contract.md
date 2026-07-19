---
subject: ethos:decision:metric-domain-budget-contract
role: decision
state: canonical
relations:
  depends_on: DR-0005
  informs: source budget, code size, changed-scope admission, compression closeout
---

# DR-0008: Metric-Domain Budget Contract

Status: accepted.

Purpose: rule that repository budgets use versioned measures inside their native
carrier and scope domains, retain ELOC for individual-file readability, and do
not treat LOC, characters, lexical tokens, semantic nodes, payload bytes, or
model tokens as interchangeable currencies.

See also: [Decision Records](../README.md), [Decision Index](../decision-index.md),
[Budget Contract v2 Design](../../plans/budget-contract-v2-design.md), and
[Product Design Contract](../../governance/product-design-contract.md).

## Record

| Field | Value |
| --- | --- |
| Decision ID | DR-0008 |
| Kind | architecture / quality governance |
| Decision Makers | ETHOS maintainer under the 2026-07-19 Budget Contract v2 instruction |
| Status | accepted |
| Decision Date | 2026-07-19 |
| Decision Version | 1 |
| Decision Change Date | 2026-07-19 |
| Record Review Date | 2026-10-19 |
| Supersedes | none |
| Superseded By | none |
| Depends on | DR-0005 (declarative runtime spine) |
| Scope | Repository-source measurement domains, carrier classification, metric versioning, non-compensating policy, per-file ELOC, and agent-token separation. |
| Boundary | Does not calibrate v2 thresholds, accept DR-0009, authorize cutover, settle debt, or claim compression completion. |
| Decision | Adopt the metric-domain vector and migration invariants defined below. |
| Consequences | v1 remains authoritative until later governed cutover; every inherited obligation stays visible. |
| Proof or Evidence | OpenSpec foundation Change, v1 fact snapshot, focused extraction regressions, claim/Chronicle, and later replay/dual-control evidence. |
| Revisit Trigger | A native metric is shown to be nondeterministic, materially gameable, unavailable for a governed carrier, or unable to preserve an inherited obligation. |

## Context

Effective code lines are useful for local reading span and oversized-file
control, but they are not stable repository-wide semantic currency. Minifying
JSON, packing Python statements, shortening identifiers, or moving behavior into
large literals and declarations can reduce line count while structure or
payload grows. Raw characters expose payload but not structure. Model-specific
BPE tokens change with tokenizer and model selection and therefore describe an
agent runtime, not repository source truth.

The predecessor Work Lane's stable v1 observation was blocked with 17 required
gaps. Before successor reconstruction, separately accepted candidate changes
projected campaign-terminal growth as advisory while retaining terminal and debt
facts. That later projection does not settle the predecessor obligations or
authorize v2; migration must preserve both the historical blocked observation
and the current policy, campaign, advisory, and debt facts rather than normalize
either away.

## Decision

1. **Measures stay inside their domains.** Programming source uses
   language-native lexical tokens and normalized syntax or payload bytes.
   Structured declarations use semantic nodes and normalized scalar payload
   bytes. Templates separate dynamic structure from static payload. Tests,
   evidence, derived projections, governance history, documentation, and product
   source remain distinct scopes.
2. **Hard coordinates do not compensate.** Repository policy is a vector over
   `(scope_id, metric_id)` and passes only when every required coordinate passes.
   Bytes cannot offset tokens, tests cannot offset product source, and one
   language or carrier role cannot silently fund another.
3. **ELOC remains local.** Effective code lines remain a hard per-file
   readability and maintainability ceiling. Repository-wide LOC enforcement may
   be retired only after DR-0009 accepts calibration, successor obligations,
   dual-control evidence, cutover, and rollback.
4. **Adapters are not currency.** AST and CST structures are parser adapters and
   diagnostics. The contract version binds parser or lexer identity, version,
   grammar digest, normalization, aggregation, and carrier rule.
5. **Inventory fails closed.** Every maintained carrier is classified exactly
   once or explicitly excluded. Zero matches, multiple matches, unsupported
   governed extensions, invalid input, unavailable parser, or metric-contract
   mismatch are required gaps.
6. **Agent tokens are separate.** LLM/BPE tokens may govern prompts, context, or
   generated-response operations. They do not enter repository-source budgets
   and do not convert repository coordinates.
7. **Migration preserves v1 truth.** The v1 baseline remains
   `2dab77f169eceb2d45f917358c2a7487e7ac8db6`. No average conversion, current-HEAD
   reset, allowance increase, expiry extension, or gap disappearance is valid.
   Each old obligation needs settlement evidence or an equal-or-stronger named
   v2 successor obligation.
8. **Admission and closeout are separate.** Default proof gains changed-scope
   source admission. Repository-wide source-budget remains full-proof and
   terminal compression evidence. Migration completion does not imply
   compression completion.

## Consequences

- Metric and carrier contracts become durable, versioned product inputs rather
  than implementation constants.
- v2 requires more explicit adapters and evidence than v1, but formatting games
  and cross-domain compensation become observable.
- The first implementation slice is behavior-preserving extraction from
  `ethos.domain.prove`; it changes ownership, not baseline, thresholds,
  campaign enforcement, required/advisory classification, or debt.
- DR-0009 remains mandatory for calibrated ceilings, Debt v2 supersession,
  dual-control acceptance, authoritative cutover, and rollback.
- Terminal compression can close only when every terminal coordinate passes and
  active, expired, unmapped, and unclassified debt counts are zero.

## Proof Or Evidence

- `openspec/changes/archive/2026-07-19-budget-contract-v2-foundation-20260719/`
- `docs/plans/budget-contract-v2-design.md`
- `docs/plans/budget-contract-v2-implementation.md`
- `evidence/chronicle/budget-contract-v2-foundation-20260719/`
- Focused source-budget extraction and command-declaration regressions.
- Later Git baseline replay, adversarial corpus, deterministic shadow, debt
  mapping, changed-scope admission, dual-control, and rollback evidence.

## Revisit Trigger

Revisit through a new OpenSpec Change and a superseding Decision Record if a
metric cannot be implemented deterministically for a governed carrier, creates
a false-negative path that the vector cannot represent, or a simpler contract
provides equal or stronger non-compensating evidence. Do not revise this record
merely to make an existing budget gap disappear.
