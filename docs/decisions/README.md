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
The linked Docs Registry owns the shared metadata, rationale and five-section
form; this entrance does not maintain another template or rule set.

- [DR-0006: Proof trust boundary](dr-0006-proof-trust-boundary.md): why local proof and independent assurance are separate claims.
- [DR-0010: Source-budget non-compensation](dr-0010-source-budget-non-compensation.md): why unrelated source classes cannot subsidize each other's growth.
- [DR-0011: Documentation portability](dr-0011-documentation-portability.md): why semantic discovery does not mandate one physical tree.
- [DR-0012: Repository paradigm](dr-0012-repository-paradigm.md): why every governed repository follows one common repository contract and which structure stays repository-owned.
- [DR-0013: Historical repair evidence reads its own policy location](dr-0013-historical-repair-policy-location.md): why moving a policy field does not reinterpret an earlier repair record.
- [DR-0014: Comparative correction](dr-0014-comparative-correction.md): why a replacement may drop an incumbent finding only when evidence outside the candidate shows it false.
