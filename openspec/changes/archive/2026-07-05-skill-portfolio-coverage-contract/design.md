## Context

The official OpenSpec boundary is `ethos-assistants` for repo-local skills and
assistant projections, with `ethos-contracts` carrying the provider-neutral
activation IR. The product boundary remains repository truth: skills are thin
procedures, and the activation registry is routing metadata.

## Design

`activation.toml` may declare a `[coverage]` table with:

- `required_primary_subjects`: subjects that must have exactly one active
  primary owner in the current portfolio.
- `single_owner_subjects`: subjects that must not have multiple active primary
  owners.

The normalized registry preserves this table. `playbooks_report` derives active
primary owners from normalized records, emits `portfolio_coverage`, and in
`v2-strict` folds violations into required gaps:

- `skill_portfolio_subject_missing:<subject>`
- `skill_portfolio_subject_duplicate:<subject>:<ids>`

This keeps the mechanism small: no new skill type, no parallel truth store, and
no host-specific routing surface. The portfolio remains intentionally small;
coverage contract validates the shape instead of multiplying entities.

## Alternatives

Adding more skills would increase surface area without proving MECE. Encoding
MECE only in prose would keep the gap invisible to CI. A separate portfolio file
would create another truth store. Reusing `[coverage]` inside activation keeps
routing and portfolio coverage in one owner while preserving repository truth
above it.

## Proof Strategy

- Unit tests for missing and duplicate primary subject gaps.
- Product payload assertion that `portfolio_coverage` reports the intended five
  primary subjects.
- OpenSpec lifecycle validation.
- Focused playbooks checks and strict proof gate.
