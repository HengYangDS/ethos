# authority-kernel-head-rename

## Why

`Authority` was a correct early boundary marker, but it became a long and
opaque name for the head of the kernel chain. The current truth needs the plainer
and more general term `Authority`: the ordered source of decision legitimacy,
truth boundary, and policy reference. The old term may remain in historical
records, but it must not remain a current code, schema, docs, or OpenSpec spec
surface.

The recovery also surfaced two related protected-root lessons: host projection
or scratch decomposition paths must stay out of accepted roots, and local lease
reads should tolerate default SQLite open failures through a read-only fallback
instead of making coordination invisible.

## What Changes

- Rename the current kernel head to `Authority` across
  active code, schemas, product docs, authority graph, and current kernel spec.
- Normalize archived OpenSpec and historical evidence vocabulary when needed so
  tracked repository scans have a single authority name.
- Classify `.claude`, `CLAUDE.md`, `.gitnexus`, `.ethos/decomp-recipes`, and
  `docs/superpowers` as forbidden protected-root projection/scratch paths.
- Add a read-only SQLite fallback for active lease reads when the default local
  connection cannot open the state database.

## Capabilities

- `kernel`: subject=authority-kernel-head; reuse=rename; change=rename; facet:lifecycle=validation; facet:surface=docs; facet:surface=schema; facet:surface=openspec; facet:authority=source; facet:authority=test; facet:authority=evidence
- `repository-governance`: subject=protected-root-projection-pollution; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=audit; facet:authority=source; facet:authority=test

## Out Of Scope

- No compatibility surface for predecessor vocabulary in historical or current tracked text.
- No compatibility alias for the superseded predecessor name in current code.
- No change to transition command semantics.
