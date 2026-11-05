# Design

## Context

See [proposal.md](proposal.md). `githubHostSupplyAt` is shared by every GitHub job. Syft is locked
for all six platforms in `.config/mise/mise.lock`.

## Goals / Non-Goals

Goals:

- The release runtime jobs declare their archives' components on every host.
- A job that runs the supply chain cannot lose Syft again without a failing test.

Non-goals:

- Staging Syft in jobs that do not run the supply chain.
- A new tag. The tag and its source are unchanged.

## Decisions

- **A parameter with a default.** `native: [...string] | *["vale"]` keeps every other job as it is.
- **A test on the projection.** It reads `.github/workflows/ci.yml` and, for each job whose steps
  run `nox -s supply_chain`, requires a native supply step that stages `syft`.

## Risks / Trade-offs

- The release run of an existing tag now uses a newer workflow than its source. The jobs verify
  the tag's commit against `release_head`, so the shipped bytes still come from the tag.
