## Why

ETHOS already resolves fresh repository facts, current authority, ordered gaps,
and one recovery action through `CurrentResolution`, but `ethos prove` continues
into proof planning after that resolution has blocked. The downstream exception
path can then replace the authoritative gap and action with unrelated adoption
or repair guidance, so identical facts no longer have one public meaning.

## What Changes

- Make a non-passing current resolution a terminal boundary for every consuming
  public operation, including proof planning.
- Preserve the resolver's verdict, ordered gaps, singular next action, and
  user-decision fact without command-local reinterpretation.
- Compile the deterministic proof plan only from the passing frozen resolution;
  keep exact live re-observation at Attestation issuance, where freshness is
  required for effect admission but intent cannot be reselected.
- Make lane migration consume commit policy from the exact current candidate
  snapshot rather than allowing historical lane policy to govern replay.
- Keep branch-role observation limited to role fields; retired transition
  declarations are neither interpreted nor allowed to block migration, while
  strict ref-mutation admission continues to require the exact current schema.
- Delete proof-local failure mapping that duplicates the current-resolution
  owner's responsibility after its remaining native planner errors are routed
  to their proper owner.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: Require failure-preserving consumption of the shared current
  resolution across public surfaces, including `ethos prove`.

## Impact

The change affects current-resolution consumption, proof command projection,
the public command-plane contract, and focused cross-surface regressions. It
does not add persistent state, a second resolver, an error registry, a
compatibility fallback, or an adopter-specific carrier; it does not weaken
issuance-time safety checks.
