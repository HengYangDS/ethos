## Context

`tools/ci/format_selection.py` fails closed for JSON paths that are neither a
declared root nor a declared exact file. The Work Lane convergence inventory is
the only tracked JSON under `evidence/chronicle/`; it is curated, digest-bound
evidence rather than generated runtime output.

## Goals / Non-Goals

**Goals:**

- Keep JSON carrier placement fail-closed.
- Admit the one tracked convergence inventory needed by the active local
  closeout program.
- Preserve an auditable, narrow policy reason and focused proof path.

**Non-Goals:**

- Do not allow all Chronicle JSON.
- Do not change JSON canonicalization, schema policy, or generated-artifact
  topology.

## Decisions

1. Add the exact inventory path to `.json` `files`, not to `roots`.
   The path is a one-off curated evidence record; a root exemption would admit
   future unrelated JSON without a policy review.
2. Reuse the existing format-selection owner script and architecture test.
   They already execute the actual tracked-file audit and previously failed on
   this exact path, so a duplicate formatter or parallel policy is unnecessary.
3. Add an explicit quality requirement rather than treating the archive as a
   mutable container. The archived convergence decision remains historical;
   this active Change owns the new quality-policy semantics.

## Risks / Trade-offs

- [The inventory is later retired while its exact exception remains] -> the
  policy review removes the entry in the same governed change that removes the
  evidence carrier.
- [A future Chronicle JSON needs admission] -> it remains blocked until its own
  Change records an exact file or reviewed carrier root.

## Migration Plan

1. Add the exact file declaration and run the format-selection owner script.
2. Run the focused architecture and CLI regression tests, then archive this
   Change through official OpenSpec semantics.
3. Refresh parity and run a new HEAD-bound proof before candidate landing.
4. Roll back by removing both the inventory and its exact file declaration in a
   future governed Change; never broaden the root as a rollback shortcut.

## Open Questions

None.
