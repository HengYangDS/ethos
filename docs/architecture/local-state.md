---
subject: ethos:local-state
role: reference
state: canonical
relations:
  canonical_for: ignored runtime state
---

# Local State

ETHOS stores host-local runtime state in `.ethos/state/state.sqlite`. The
directory is ignored except for `.ethos/state/.gitignore`.

SQLite records coordination and replay aids. It does not pre-create
speculative cache stores; action cache keys stay in action-graph contracts
until a concrete runtime cache earns its own owner and lifecycle.

- `schema_migrations`
- `events`
- `sessions`
- `leases`
- `gate_runs`
- `action_runs`
- `evidence_index`

Chronicle events may also be stored locally for fast inspection. Durable truth
remains repository files, schemas, claims, and evidence records. Local state can
be deleted and rebuilt without changing repository history.

Work Lane leases are local coordination facts recorded by lane-start flows. They
support future ownership, handoff, and closeout ordering checks, but they do not
replace Git history, OpenSpec records, claims, or evidence. Current prewrite and
apply-mode admission are enforced by checkout role, editor-root binding, and
HEAD checks; lease ownership enforcement is a later lifecycle extension.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
