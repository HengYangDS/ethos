---
subject: quality:coordination-lifecycle-edge-compression
reuse: extend
change: modify
facet:lifecycle: validation
facet:surface: test,openspec,evidence
facet:authority: source,test,openspec,claim,evidence
---

## Why

`test_coordination_lifecycle_edges.py` contains repeated coverage-only setup and
scalar normalization probes that add executable test surface without covering
independent coordination behavior. The global compression program requires such
test, tool, and fixture duplication to be removed before terminal budget
settlement.

## What Changes

- Consolidate only uniform lifecycle-edge assertions into literal case tables.
- Remove duplicate shared-normalizer scalar probes and retain one named
  normalizer boundary.
- Preserve separately named handoff, lease, persistence, and ref-transition
  effect boundaries.

## Capabilities

- `quality`: subject=coordination-lifecycle-edge-compression; reuse=extend;
  change=modify; facet:lifecycle=validation; facet:surface=test,openspec,evidence;
  facet:authority=source,test,openspec,claim,evidence

## Impact

- `tests/unit/coverage/test_coordination_lifecycle_edges.py`
- `openspec/specs/quality/spec.md`
- Test-only evidence and claim carriers; no production API, schema, dependency,
  or runtime behavior changes.

## Out Of Scope

- Production coordination, lease persistence, handoff protocol, CLI payload,
  schema, or dependency changes.
- A generic test DSL or a reimplementation of lifecycle semantics in test code.
