## Design

The hardening is intentionally policy-first. The existing docstring quality
command already computes public product-surface coverage and reports 100 percent
on the current repository. This change makes that achieved state the enforced
floor by raising the repository-owned policy to 100.

The gate boundary stays unchanged:

- trust-bearing coverage applies to product-visible Python surfaces;
- broader public-looking definitions remain a non-blocking inventory;
- the reusable CI script remains the execution owner;
- Ruff remains the structured-style companion, not the coverage authority.

## Tradeoffs

A 100 percent floor is stricter than the previous 95 percent floor. That is
acceptable because the current public-surface set is already documented, and new
public surfaces should carry intent before they enter the product API.

## Risks

If the public-surface classifier expands, the gate may reveal newly required
Docstrings. That is intended: classifier expansion changes the governed surface
and should be handled with evidence rather than silent tolerance.
