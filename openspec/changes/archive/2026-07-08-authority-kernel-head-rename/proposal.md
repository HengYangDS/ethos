# authority-kernel-head-rename

## Why

The retired authority-head token was a correct early boundary marker, but it
became a long and opaque name for the head of the kernel chain. The current truth needs the plainer
and more general term `Authority`: the ordered source of decision legitimacy,
truth boundary, and policy reference. The old term may remain in historical
records, but the token itself must not remain in repository records, current or archived.

The recovery also surfaced two related protected-root lessons: host projection
or scratch decomposition paths must stay out of accepted roots, and local lease
reads should tolerate default SQLite open failures through a read-only fallback
instead of making coordination invisible.

## What Changes

- Rename the current kernel head to `Authority` across
  active code, schemas, product docs, authority graph, and current kernel spec.
- Keep archived OpenSpec and historical evidence meaning as historical record
  while removing the retired token.
- Classify `.claude`, `CLAUDE.md`, `.gitnexus`, `.ethos/decomp-recipes`, and
  `docs/superpowers` as forbidden protected-root projection/scratch paths.
- Add a read-only SQLite fallback for active lease reads when the default local
  connection cannot open the state database.

## Capabilities

- `kernel`: subject=authority-kernel-head; reuse=rename; change=rename; facet:lifecycle=validation; facet:surface=docs; facet:surface=schema; facet:surface=openspec; facet:authority=source; facet:authority=test; facet:authority=evidence
- `repository-governance`: subject=protected-root-projection-pollution; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=audit; facet:authority=source; facet:authority=test

## Out Of Scope

- No loss of historical chronicle or archived OpenSpec meaning.
- No compatibility alias using the retired authority-head token in current code.
- No change to transition command semantics.
