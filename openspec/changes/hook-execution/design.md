## Execution Boundary

Git supplies a fixed protocol, not an interactive CLI request. Its thin launcher
selects the same immutable package and invokes the native protocol owner directly.
The protocol owner validates input before loading the existing admission machinery.
Notifications and unrelated updates neither inspect runtime bytes nor initialize
the command tree, policy compiler or proof machinery. Invalid input fails closed.

Prepared branch updates still select and fully validate the current runtime once
per invocation, then invoke existing ref policy and exact compensation behavior.
Other hook kinds retain their existing admission. Nothing is cached across effects.
The old CLI `hook run` transport and sibling hook module are removed, not aliased.

## Alternatives

- A shell fast path duplicates Git semantics outside their Python owner.
- Raising concurrency amplifies repeated imports and process creation.
- A global cache of status, runtime integrity or authorization can hide changes.
- Replacing all lifecycle fixtures would mix assurance redesign with this bounded
  execution repair; measured remaining costs stay on the existing P5 route.

## Verification And Migration

First deny unused imports in an actual native entry invocation and observe RED.
Retain real malformed envelopes, damaged-runtime rejection, one-observation batch
behavior, raw commit rejection and the existing complete lifecycle journey.
Compare cold and warm invocations under the same environment, not a fixed
wall-time assertion. The full proof and package activation remain separate claims.

Update the package launcher contract and all direct callers atomically. Existing
installed bytes are not modified; public installation selects the accepted new
generation. No compatibility transport remains in the new package.
