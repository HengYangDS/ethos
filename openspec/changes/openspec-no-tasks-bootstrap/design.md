## Context

ETHOS obtains the lifecycle list from the official OpenSpec CLI, then uses that
same selection for `selected_change`, lifecycle review, and adopter companion
scope binding. Official OpenSpec 1.6 assigns the status `no-tasks` to a newly
created Change before any planning artifact exists. The previous state filter
ignored it, producing a deadlock: the scope guard required a selected Change,
while the first scope companion could not be written until the guard selected
the Change.

## Goals / Non-Goals

**Goals:**

- Interpret `no-tasks` as an official active, non-complete Change.
- Preserve the existing scope guard: only the exact absent, untracked
  `scope.toml` for that selected Change can bootstrap.
- Keep all ordinary material-path writes covered only after a valid companion
  declaration exists.

**Non-Goals:**

- Relaxing lifecycle completeness, official validation, claim binding, or proof.
- Changing the official OpenSpec package, schema, on-disk session state,
  credentials, or hosted CI behavior.

## Decisions

1. **Use one explicit state in both lifecycle selectors.** Add `no-tasks` to
   both the default selected-Change priority groups and `_lifecycle_names`; this
   avoids a selected Change and the scope reader disagreeing about authority.
2. **Place it below `in-progress`.** A started Change remains the higher-priority
   active work item. `no-tasks` precedes archiving and complete records because
   it is still an unfinished official Change.
3. **Reuse existing bootstrap constraints.** No new write exception is added.
   The current scope reader already requires one requested path, one selected
   Change with a missing scope, an existing Change directory, and an untracked
   exact companion path.

## Risks / Trade-offs

- **A bare Change could cover ordinary work** -> regression tests require the
  ordinary material path to stay rejected before its scope companion exists.
- **State-order drift could select completed history first** -> regression
  covers a newer complete Change and asserts `no-tasks` still wins.
- **A later official state could be misunderstood** -> unknown statuses remain
  excluded until they are explicitly modeled and tested.

## Migration Plan

1. Add the RED regressions for selector precedence and scope bootstrap.
2. Add `no-tasks` to the two shared lifecycle filters.
3. Run focused tests, strict OpenSpec validation, lifecycle/claim checks, and
   final exact-HEAD proof before normal candidate integration.

Rollback is the two-line state-filter reversal; it restores the former
fail-closed behavior but also restores the bootstrap deadlock.

## Open Questions

None. The official CLI currently exposes the exact `no-tasks` state observed
by this carrier.
