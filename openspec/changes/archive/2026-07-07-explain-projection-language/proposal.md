# Explain Projection Language

## Problem

`ethos explain` payloads can now explain required gaps and advisory signals, but
CLI help and command-plane docs still described the command as required-gap-only.
That projection drift makes small-signal governance look like blocking-only
semantics.

## Change

Align CLI help and command-plane docs with the command payload: explain projects a
governance gap or advisory signal into the invalid-state taxonomy.
