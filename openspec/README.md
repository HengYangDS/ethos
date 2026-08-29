# ETHOS OpenSpec Workspace

This workspace uses official OpenSpec artifacts as the sole tracked carrier for
change intent, requirements, design, task progress, validation, and archive
history.

OpenSpec is the selected native carrier for the ETHOS self profile and every
mutation-capable adopter, but it is not part of the vendor-neutral semantic
kernel or a second ETHOS public command plane. Observation-only repositories may
omit it. The official OpenSpec CLI owns workspace authoring, validation, and
archive operations; ETHOS consumes exact official observations without adding a
tracked change schema.

## Product Protocol

- Accepted capability identity and behavior live only at
  `openspec/specs/<capability>/spec.md`.
- A proposal names each affected capability with exactly `subject`, `reuse`, and
  `change` intent.
- Active Change IDs are date-free lower-kebab identifiers that start with a
  letter; intent lives under `openspec/changes/<change-id>/`.
- Changed behavior lives in that Change's delta specs.
- Historical carriers use exactly one archive date:
  `openspec/changes/archive/YYYY-MM-DD-<change-id>/`.
- Archived changes are history after closeout, not reusable active work
  containers.

Every non-trivial self-profile governance mutation should have one selected
active Change. A completed Change remains active and blocks integration until
the owner-native archive operation removes it from official active state.

ETHOS compiles one exact official Change projection into a transient Commitment
containing only `schema_version`, `id`, and `acceptance`. Changed paths and
repository coordinates are fresh Git Facts. Work ownership is the separate
four-field Lease relation: `lane_ref`, `holder_ref`, `generation`, and
`expires_at`.

One official Change owns one bounded intent and its task progress. Sequence and
dependencies are derived from official artifacts, Git history, and selected
Attestations only when they affect current admission; ETHOS persists no parallel
relation record. Research questions and procedures stay in official proposal,
design, spec, or task content. Results and completed proof are Attestations.
Archived Changes remain inert and do not participate in a current verdict.

OpenSpec checkboxes own obligations that can be completed before archive. An
archive, proof of the resulting HEAD, candidate or protected-ref advance, hosted
review, and publication are effects whose subject does not exist until the prior
transition succeeds; they remain mandatory through exact Attestations and receipts,
not unchecked boxes that would make archive admission circular.

## Proof

Validate the carrier with its native owner, then compile the governed plan:

```bash
openspec validate --all --strict --json
ethos plan --changed --json
```

ETHOS validates and compiles the exact official projection while consuming
official `doctor`, `list`, `status`, and strict `validate` observations. It
derives changed paths and ref coordinates from fresh Git facts. Historical
archive bytes remain non-authorizing history and are not scanned as an active
database.
