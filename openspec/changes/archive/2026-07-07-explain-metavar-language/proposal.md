# Explain Metavar Language

## Problem

`ethos explain` accepts a governance gap or advisory signal, and its docs already
say `<gap-or-signal>`, but the generated CLI usage still showed `GAP`. That kept
a subtle required-gap-only projection in the command's most visible UX surface.

## Change

Rename the CLI positional parameter to `gap_or_signal` while preserving the JSON
compatibility field `summary.gap` and the taxonomy payload semantics.
