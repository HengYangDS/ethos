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

SQLite records coordination and replay aids:

- `schema_migrations`
- `events`
- `sessions`
- `leases`
- `gate_runs`
- `action_runs`
- `evidence_index`
- `cache_entries`

Chronicle events may also be stored locally for fast inspection. Durable truth
remains repository files, schemas, claims, and evidence records. Local state can
be deleted and rebuilt without changing repository history.
