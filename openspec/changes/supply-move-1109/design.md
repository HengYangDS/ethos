# Design

## Context

See [proposal.md](proposal.md). Releases are admitted only after 24 hours, the age that Mise
enforces on its own tools. The GitLab supply image's manifest hashes both uv locks, the npm lock
and the Mise files, so any move needs a rebuilt image.

## Goals / Non-Goals

Goals:

- Every lock holds the newest stable release that has been public for at least 24 hours.
- No override remains whose reason its dependency has fixed.

Non-Goals:

- Taplo's move to a native supply, which has its own Change.
- Mise itself, whose host pin its owner keeps, and Python 3.15, outside `requires-python`.

## Decisions

- **Native cutoff.** `uv lock --upgrade --exclude-newer=<cutoff>` sets the age and a plain
  `uv lock` drops the persisted option; npm resolves with `--before=<cutoff>`.
- **Retire the dompurify override.** `@allurereport/web-commons` 3.33.0 asks `dompurify ^3.4.17`,
  the version the override forced; the dependency audit must still pass without it.
- **Bind the image in a second commit.** The image is built from the commit that moves the files,
  on the lane's proposal ref, and its digest and source commit are bound afterwards.

## Risks / Trade-offs

- cachetools 8.0.0 is a major release; it is a transitive dependency, so the suite decides.
- A newer ruff or ty may add findings; the precheck and the impacted sweep find them before the
  proof.
