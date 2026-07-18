# OpenSpec Changes

Active change folders are ETHOS case carriers. They record intended change and
review state; they do not supersede source, tests, schemas, governed docs,
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

When an adopter declares material paths, add the ETHOS-owned companion:

```toml
# openspec/changes/<change-id>/scope.toml
schema_version = 1
paths = ["docs/governance/**", "openspec/changes/<change-id>/**"]
```

The companion binds material changed paths to the official active or archiving
Change selection; it does not alter the official OpenSpec workflow schema.
Create the Change with the official `openspec new change <change-id>` command
first. Prewrite may bootstrap only that exact absent companion. Thereafter it
must validate and cover itself as well as all material writes; no whole Change
directory is exempt from admission.

Use `template.md` as the authoring scaffold and validate with:

```bash
ethos openspec --lifecycle --json
```

Lifecycle validates archiveability through the configured official archive CLI
in a disposable workspace copy. It never archives or rewrites this source
change; an application-time conflict must be repaired before plan, proof, or
land can proceed.

## Completion Grammar

An archived carrier's checklist may assert only work that was completed before
archive. The archive-closeout gate correctly blocks any unchecked archived task.
Candidate landing, accepted-root closeout, Work Lane retirement, and remote
publication therefore belong to explicit post-archive lifecycle transitions:
record their boundary in the carrier, but do not leave them as unchecked archive
tasks or mark them complete before the transition occurs.
