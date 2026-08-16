# Design

## Context

An active OpenSpec Change is mutable work; an archived Change is immutable
history. A terminal repository state may therefore contain no active Change.
Tests and documentation that hard-code an active carrier path contradict the
public archive lifecycle.

## Decision

Validate active Change carriers as a bounded set of at most one. When the set is
non-empty, retain the existing identity, dependency, acyclicity, task uniqueness,
and task-to-proof checks. When it is empty, the terminal state is valid.

Historical design references bind directly to the dated archive carrier. No
fallback lookup, compatibility alias, reopened archive, or second progress owner
is introduced.
