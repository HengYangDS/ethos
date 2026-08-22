## Why

`repository-audit` can currently return `pass` after a collection of local
checks while its own design-integrity report says semantic equivalence was not
evaluated. Set-based reference closure also erases provenance, so duplicate
owners and orphan producer/consumer/selector relations can be invisible. This
is a false-positive authority gap at the repository's principal read-only
governance gate.

## What Changes

- Make repository audit compile one finite semantic-closure observation from
  current tracked declarations and carriers.
- Preserve provenance long enough to detect missing, duplicate, orphan,
  superseded, conflicting, and unknown relations instead of deduplicating them
  before evaluation.
- Make current carrier boundaries explicit so historical evidence, archived
  Changes, examples, and negative fixtures cannot become current semantic
  owners.
- Project the typed closure through the existing `repository_audit()` owner and
  delete overlapping partial report ownership.
- Keep audit observational: it neither stores a graph nor mints authority.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: repository quality requires a closed, provenance-preserving
  semantic ownership relation rather than isolated green checks.
- `repository-governance`: the canonical repository audit fails closed when
  current owners, producers, consumers, or selectors do not form one complete
  relation.

## Impact

- Repository audit composition and result shape.
- Product-reference declaration and observation helpers.
- Design-integrity projection and documentation registry boundaries.
- Architecture and unit tests for false-positive audit cases.

Out of scope: a graph database, semantic ledger, NLP inference, mutation
authority, historical-carrier rewriting, or a second audit command.
