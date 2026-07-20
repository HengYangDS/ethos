## Why

The canonical Python policy still suppresses one `S606` finding through both
the Ruff ignore list and ignored-rule ratchet. The finding is an obsolete
Python-version bootstrap in the quality-audit owner script, although ETHOS
requires Python 3.12 or later.

## What Changes

- Remove the obsolete host-side re-exec bootstrap from `quality_audit.py`.
- Remove `S606` from both canonical Ruff exception carriers.
- Add regressions that keep the retired bootstrap and both exception carriers
  from returning.
- Bind the correction to a whole-corpus rule probe, owner gate, OpenSpec, Claim,
  Chronicle, and head-bound proof.

## Capabilities

### Modified Capabilities

- `quality`: direct `S606` enforcement; subject=quality:python-s606;
  reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=ci;
  facet:authority=source.

## Out Of Scope

- Remaining quality debt, foreign Work Lanes, hosted CI, remote publication,
  and terminal exception-free quality.
