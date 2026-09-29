---
subject: docs:decisions
role: index
state: canonical
relations:
  canonical_for: durable decision navigation
---

# Decisions

Status: canonical navigation; records retain rationale, not current executable authority.

Purpose: find choices whose alternatives and revisit conditions remain useful across Changes.

See also: [Documentation Root](../README.md) and
[Docs Registry](../governance/docs-registry.md#directory-entrypoint-rule).

Records use `dr-<four-digit-id>-<semantic-topic>.md`. The number is a stable
decision identity, never reused for another ruling; the topic remains readable.
This README is the only navigation, not a second decision registry.
Historical `DR-0009` was reserved for budget calibration and is not reassigned.

- [DR-0006: Proof trust boundary](dr-0006-proof-trust-boundary.md): why local proof and independent assurance are separate claims.
- [DR-0010: Source-budget non-compensation](dr-0010-source-budget-non-compensation.md): why resource budgets cannot offset quality failures.
- [DR-0011: Documentation portability](dr-0011-documentation-portability.md): why semantic discovery does not mandate one physical tree.
