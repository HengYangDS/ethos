## Context

The current installer performs these operations in sequence:

```text
materialize runtime -> materialize hooks -> switch CURRENT/config -> read later
```

SQLite schema validation occurs only when a later command reads Lease state.
The previous table stores `id, subject, owner, expires_at, payload_json`; the
terminal table stores only `lane_ref, holder_ref, generation, expires_at`.
Previous payloads already contain the four terminal values as `lane_ref`,
`holder_ref`, `epoch`, and `expires_at`, so a recognized exact row can be
projected without retaining its obsolete Commitment, HEAD, tree, scope, or
workflow fields.

## Decision

### One runtime activation transaction

Hook installation remains the sole public owner. It first resolves the exact
runtime inputs, exports one hashed requirements file, and installs that closure
into an owned temporary target. This single network-capable step may only fill
the Git-common cache and the temporary target; it occurs before selector, hook
configuration, or state mutation. The target is then deleted. Construction of
the immutable runtime installs the same requirements with `--offline`, so a
successful activation proves that the filled cache contains the exact closure.

After immutable runtime and hook generations exist, installation opens one
exclusive SQLite transaction. It validates current state or stages the exact
legacy-to-terminal Lease projection without committing. While that transaction
is held, installation switches `CURRENT` and Git-common hook configuration and
post-observes the runtime binding. Success commits SQLite last; failure rolls
SQLite back and restores the exact prior selector and configuration.

No durable migration ledger is added. The public result reports before/after
schema state, row disposition, and whether migration, reset, or recognition
occurred.

### Positive legacy admission

Automatic migration accepts only the exact previous table/index shape, no
triggers, and rows whose redundant columns and payload agree on lane, holder,
generation, and expiry. It projects:

```text
subject       -> lane_ref
owner         -> holder_ref
payload.epoch -> generation
expires_at    -> expires_at
```

Any ambiguity or malformed row blocks before activation. The sole recovery is
an explicitly authorized reset through `ethos hook install --reset-state
--authorize --json`, which drops only the obsolete Lease relation and creates
the terminal empty relation in the same activation transaction. Reset does not
claim ownership of existing Work Lanes; subsequent status reports them as
unbound for normal recovery.

### Managed cache fill and offline closure

For locked package runtimes, ETHOS exports the exact hashed requirements once.
It performs one exact hashed sync into an owned temporary target to fill the
Git-common cache, deletes that target, and then installs the immutable runtime
from the same requirements with network access disabled. It does not use a
dry-run as proof because a resolver may report success while still saying that
artifacts would be downloaded. Actual offline installation is the proof.

## Deletion

- Do not add a long-lived schema version table, migration registry, backup
  database, compatibility reader, or hidden reset script.
- Do not preserve obsolete Lease payload semantics after projection.
- Delete command-level generic retry guidance for this failure; project the one
  exact install or authorized reset command instead.
