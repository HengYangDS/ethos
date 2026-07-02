# OpenSpec Changes

Active change folders are ETHOS case carriers. They record intended change and
review state; they do not supersede source, tests, schemas, current docs,
accepted specs, claims, or evidence until closeout promotes those surfaces.

Create a new folder for non-trivial governance semantics. Do not reuse an
archived or complete change as the default container for new work.

A complete active change must contain:

- `proposal.md` with capability metadata and out-of-scope boundaries.
- `design.md` for new capabilities, extracted ownership, topology changes,
  product-shape changes, or cross-surface governance changes.
- `tasks.md` with review-sized checklist items.
- `specs/<capability>/spec.md` deltas using official OpenSpec sections.
- an active trust-bearing claim whose `carriers.openspec` points at the change.

Use `template.md` as the authoring scaffold and validate with:

```bash
ethos openspec --lifecycle --json
```
