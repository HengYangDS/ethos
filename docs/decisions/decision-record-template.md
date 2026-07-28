---
subject: ethos:decisions:template:decision-record
role: template
state: canonical
relations:
  canonical_for: new decision record drafting
---

# DR-XXXX: Title

Status: proposed.

Purpose: state the durable ruling and why it is needed.

See also: [Decision Records](README.md) and [Decision Index](decision-index.md).

## Record

| Field | Value |
| --- | --- |
| Decision ID | DR-XXXX |
| Kind | governance |
| Decision Makers | Named authority or role |
| Status | proposed |
| Decision Date | YYYY-MM-DD |
| Decision Version | 1 |
| Decision Change Date | YYYY-MM-DD |
| Record Review Date | YYYY-MM-DD |
| Supersedes | None |
| Superseded By | None |
| Scope | Exact semantic scope |
| Boundary | What this ruling owns and excludes |

## Context

State the observed problem and evidence without deciding it twice.

## Invariants

- Name each proposition every option must preserve.

## Alternatives Considered

### Option A: Selected candidate

**Pros**

- State concrete benefits against the invariants.

**Cons**

- State concrete costs and risks.

**Why Rejected**

Not rejected; selected below.

### Option B: Real alternative

**Pros**

- State concrete benefits against the same invariants.

**Cons**

- State concrete costs and risks.

**Why Rejected**

State the violated invariant or inferior trade-off. If no second legal option
exists, prove why the alternative class is invalid rather than inventing one.

## Selected Approach And Rationale

Select exactly one option and explain why it best preserves the invariants.

## Consequences

State positive, negative, migration, and operational consequences.

## Proof Or Evidence

Name current commands, tests, artifacts, or observations that can verify the
ruling without treating old evidence as current fact.

## Revisit Trigger

Name falsifiable conditions that reopen this decision.

## Decision Change Ledger

| Version | Date | Change | Reason | Evidence |
| --- | --- | --- | --- | --- |
| 1 | YYYY-MM-DD | Initial ruling | Initial selection | Evidence reference |
