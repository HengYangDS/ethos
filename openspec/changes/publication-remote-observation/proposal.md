## Why

Exact remote publication can stop before observing peer refs, for example when
the local source object is not trusted. The CLI currently treats the absent
observation as a successful observation and indexes `object_oid`, replacing the
real admission gap with an uncaught traceback.

## What Changes

- Consume remote-ref observations only when the effect adapter actually
  produced a complete present-or-absent fact.
- Preserve upstream source, trust, target, and remote-observation gaps without
  inventing an OID or a second availability judgment.
- Return the ordinary structured publication result for every pre-observation
  failure.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: Extend remote publication epistemic preservation to
  cover failures that occur before any peer/ref observation exists.

## Impact

The change affects the publication CLI's consumption of the existing remote
effect adapter and focused publication regressions. It adds no provider branch,
fallback observer, compatibility path, or persistent state.
