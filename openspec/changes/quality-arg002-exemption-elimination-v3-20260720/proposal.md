## Why

The canonical Python lint policy still suppresses one `ARG002` finding through
both its global Ruff ignore list and ignored-rule ratchet baseline. The rule is
selected and applies to governed code; it must therefore return to direct
owner-gate enforcement.

## What Changes

- Make dry-run planning resolve its declared execution root without running an
action.
- Remove `ARG002` from both Ruff exception carriers.
- Bind the correction to a regression, whole-corpus rule probe, canonical owner
lint gate, and native lifecycle proof.

## Capabilities

### Modified Capabilities

- `quality`: direct `ARG002` enforcement; subject=quality:python-arg002;
  reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=ci;
  facet:authority=source.

## Out Of Scope

- Remaining Ruff debt, foreign Work Lanes, hosted CI, remote publication, and
terminal exception-free quality.
