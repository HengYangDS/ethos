# Design

## Context

See [proposal.md](proposal.md). The profile owner (`repository/profile.py`) validates with Pydantic
and discards the error. Every command reaches the same `profile_failure_result`, through the CLI's
`ValueError` boundary, the application decorator, or the land and publish operations.

## Goals / Non-Goals

Goals:

- An agent learns every problem key from one result, with no value repeated.

Non-goals:

- A repair for retired profile keys; that is a paradigm obligation of its own, if the keys retire.
- Any change to the stable gap or the verdict.

## Decisions

- **Problems are codes, not messages.** Each Pydantic error becomes `<type>:<dotted location>`, and
  a TOML syntax error becomes `toml_invalid`. Messages and inputs are dropped, so no profile value
  reaches the result.
- **The profile carries its problems.** `RepositoryProfile.problems` is part of the observed
  profile, so every caller that already loads the profile can project them; the failure result takes
  the profile instead of reloading it.
- **Bounded.** The result keeps the first 20 problems and the total count, well inside the result
  budget.

## Risks / Trade-offs

- Pydantic's error types are part of the result. They are stable across Pydantic 2 releases, and a
  change would only rename a code, never hide a problem.
