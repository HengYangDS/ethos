# Design

## Context

See [proposal.md](proposal.md). ETHOS takes a release only after it has been public for 24 hours,
applied when locking with uv's `--exclude-newer`. A plain `uv lock` afterwards drops the persisted
cutoff.

## Goals / Non-Goals

Goals:

- Take every locked package's newest release that is at least 24 hours old.

Non-goals:

- Releases younger than 24 hours. filelock 4.2.9 and platformdirs 4.14.5 wait for the next move.

## Decisions

- One lock move for every eligible package, rather than one move per package.
- The supply image is rebuilt and bound in this Change, because GitLab jobs check the lock against
  the image's manifest.

## Risks / Trade-offs

- joserfc moves by a minor version. Its consumer is FastMCP's authentication path. The MCP tests and
  the full proof cover it.
