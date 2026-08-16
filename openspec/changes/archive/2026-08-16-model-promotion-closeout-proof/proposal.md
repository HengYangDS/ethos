# Change: Preserve model-promotion closeout proof after archive

## Why

The governed archive correctly moved `model-promotion` into immutable history,
but one architecture test and two design links still required its former active
path. Post-archive proof must validate the terminal state rather than recreate
or mutate the archived Change.

## What Changes

- Bound the active Change graph to zero or one complete carrier instead of one
  hard-coded historical Change name.
- Link terminal design history to the dated immutable archive carrier.

## Impact

- Affected surfaces: one architecture test and one terminal design section.
- No runtime, schema, permission, quality-threshold, or adopter behavior change.
