# Design

## Context

See [proposal.md](proposal.md). Each generated GitLab verification job's variables are the
unification `{GIT_DEPTH: "0"} & policy.gitlab.variables & runner.variables`. Because CUE refuses
two different concrete values for one field, neither the repository nor a runner can weaken full
history.

## Goals / Non-Goals

Goals:

- A Windows job retries a failed source checkout, as GitLab natively supports.

Non-goals:

- Changing Linux or macOS jobs, which showed no such failure.
- Excluding the tool cache from `git clean`.

## Decisions

- Add `GET_SOURCES_ATTEMPTS: "3"` to the base variables for runners whose `system` is `windows`.
  The same unification that protects `GIT_DEPTH` makes a different declared value a compilation
  failure, so the retry cannot be turned off by a runner declaration.
- Three attempts covers the observed window. Both failures followed the previous job by less than
  10 seconds, and every job after more than 60 seconds succeeded.

## Risks / Trade-offs

- A real checkout failure takes up to two more attempts before the job fails.
