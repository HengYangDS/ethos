# Design

## Context

See the [proposal](proposal.md). `readme_disposition_gaps` owns README presence and routing and is
pinned at a cognitive complexity of 18 (`tests/fixtures/decision-density-baseline.json`), so it
cannot take more branches; `health.py` holds 447 of its 500 effective lines.

## Goals / Non-Goals

Goals:

- A README is navigation: one role, one bound, decidable from the registry entry and the file.

Non-Goals:

- Judging whether a README links every child, or repairing a README's content.

## Decisions

1. A new function `readme_role_gaps(root, registry)` in `health.py` reads each registered
   `README.md`: a role other than `index` yields `docs_readme_not_index:<path>`, and more than 100
   nonblank lines yield `docs_index_too_long:<path>:<lines>>100`. It counts nonblank lines as the
   document length check does, and `docs_health_report` adds its gaps beside the README disposition
   gaps.
2. The bound is a named constant, not a repository parameter: the measured fleet maximum is 84, and
   a repository that needs more navigation splits its directory.

## Risks / Trade-offs

- Two governed repositories carry non-index READMEs today; their owner converts them in the lanes
  that bind this release (policy and how-to bodies move to named pages, index-shaped pages change
  role only).
