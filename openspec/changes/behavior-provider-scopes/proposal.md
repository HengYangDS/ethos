# Proposal

## Why

The behavior provider reads one combined coverage figure from a native report. Two measured
cases in governed repositories do not fit it:

- One repository judges coverage for each scope: it asks the coverage tool for a report of each
  scope with its own floor and reads the exit status. The native reports no longer carry the
  decision, so a provider that reads one percent cannot see a floor for a scope.
- No provider reads a lint, type-check, import-contract, dependency-declaration or advisory
  report. One repository runs those five as command gates judged by exit code, and one type
  checker's report lists no artifacts. This second case is relayed and not measured here.

## What Changes

Candidates, none decided:

- The provider learns declared scopes with their floors, or it trusts the declared command's exit
  and says so in its result.
- Report-reading providers for the five kinds, each with a named consumer first.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The quality providers and their declarations. It follows the provider rows in the order after
0.2.0.

Owner: the release lead. Next action: place it with the provider rows after 0.2.0. Read again:
after 0.2.0.
