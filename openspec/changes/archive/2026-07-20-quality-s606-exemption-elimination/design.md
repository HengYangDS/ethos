## Context

The Python project contract is `requires-python >=3.12`; nevertheless,
`quality_audit.py` preserves a Python-before-3.11 `uv` re-exec path. The path
is the only tracked-corpus `S606` finding and is suppressed by both canonical
Ruff exception carriers.

## Design

The governed owner script now executes directly in the project runtime. This
removes obsolete host adaptation rather than adding a second launcher or a
compatibility branch. With no remaining finding, `S606` leaves the global
ignore list and exact ratchet baseline, returning to direct enforcement by the
existing Ruff owner.

## Alternatives

1. Keep the bootstrap and add a local exemption: rejected because it preserves
   obsolete runtime support and suppresses a hard rule.
2. Keep a zero ratchet baseline: rejected because direct enforcement remains
   disabled.
3. Remove the obsolete bootstrap: selected because the repository runtime
   contract already excludes it and no public audit behavior changes.

## Proof Strategy

Run focused quality contracts, a whole-tracked-corpus `S606` probe, the
canonical Ruff owner, strict OpenSpec validation, claim validation, and a
current-HEAD executed proof before candidate integration.
