## Context

The terminal product design already points repository memory at
`evolution/ledger.toml`. Keeping live hypotheses under docs created a parallel
truth store and weakened campaign closeout.

## Design

Use `evolution/ledger.toml` as the single ledger for typed evolution entries and
hypotheses. Documentation may link to the ledger, but does not duplicate the
records. The schema admits the existing typed-entry prelude and the hypothesis
records in one TOML document.

This is a reduction, not a new subsystem: one ledger, one schema, one command
reader, one audit path.

## Proof Strategy

- Campaign hypothesis CLI reads `evolution/ledger.toml`.
- Schema validation validates `evolution/ledger.toml`.
- Repository audit requires `evolution/ledger.toml` and no longer requires the
  docs ledger path.
- Tests cover missing, malformed, and valid ledger behavior.
