# OpenSpec Changes

Active Change folders are ETHOS case carriers. Their `<change-id>` is a
date-free lower-kebab identifier beginning with a letter; a terminal
`YYYYMMDD` suffix is not part of the logical identity. They record intended change and
review state; they do not supersede source, tests, schemas, governed docs,
accepted specs or evidence until closeout promotes those surfaces.

Create a new folder for non-trivial governance semantics. Do not reuse an
archived or complete change as the default container for new work.

A complete active change must contain:

- `proposal.md` with capability metadata and out-of-scope boundaries.
- `design.md` for new capabilities, extracted ownership, topology changes,
  product-shape changes, or cross-surface governance changes.
- `tasks.md` with review-sized checklist items.
- `specs/<capability>/spec.md` deltas using official OpenSpec sections.
- `commitment.toml` with the governed repository subject and bounded scope.

Declare active material coverage in the same Commitment:

```toml
# openspec/changes/<change-id>/commitment.toml
schema_version = 1
id = "change:<change-id>"
intent = "Describe the intended outcome."
subjects = ["repository:self"]
scope = ["docs/governance/**", "openspec/changes/<change-id>/**"]
```

The contract binds material paths to the official active Change selection; it
does not alter the official OpenSpec workflow schema. Create the Change with the
official `openspec new change <change-id>` command, then add its contract before
material writes. No parallel scope carrier or bootstrap exception exists.

Use `template.md` as the authoring scaffold and validate with:

```bash
openspec validate --all --strict --json
ethos plan --changed --json
```

The official archive creates exactly one dated history path:
`openspec/changes/archive/YYYY-MM-DD-<change-id>/`. The official OpenSpec CLI is
the sole owner of that mutation. ETHOS observes official active state and never
archives, copies, or predicts archive in a disposable workspace.

## Completion Grammar

The active carrier's checklist may assert only work already completed. Official
OpenSpec completion and archive semantics govern whether that carrier can move
to history. After archive, ETHOS verifies existing Attestations through their
exact bindings; it does not reinterpret historical tasks, metadata, names, or
deltas to authorize or block a new transition. Candidate landing, accepted-root
closeout, Work Lane retirement, and remote publication remain separate ETHOS
effects with separate evidence.
