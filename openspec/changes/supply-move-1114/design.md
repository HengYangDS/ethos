# Design

## Context

See the [proposal](proposal.md). The release age is zero by the owner's decision of 2026-11-13, so
the move takes every stable release that is public at the lock step. The CI supply image is built
from the committed locks on the lane's proposal ref and bound by digest.

## Goals / Non-Goals

Goals: every locked supply at its newest stable release at the lock step.

Non-Goals:

- `complexipy` 9, whose scores need the decision-density baseline pinned again.
- Python 3.15, which stays outside `requires-python`.
- Any prerelease channel.

## Decisions

1. One lock step for every ecosystem, with its time recorded in the tasks. `uv lock --upgrade`
   moves the Python lock, and an upgrade dry run after it reports no change.
2. A hold is a resolver constraint, not a second bound. The dependency declaration check admits one
   lower bound per direct requirement, equal to its locked version, so `complexipy` keeps
   `>=8.3.0` and `[tool.uv] constraint-dependencies` holds it below 9 with the reason beside it.
3. The Mise lock keeps its format revision, and only the moved tools' entries change. CPython
   3.14.10 is locked to the 20261110 archives because Mise 2026.11.6 fetched that build on Linux
   arm64 and compared it with the locked checksum of the older one.
4. The six bootstrap digests are the ones the release's `SHASUMS256.txt` publishes.
5. The supply image build on the proposal ref is the hosted test of Mise 2026.11.8 with
   `install --locked` on Linux arm64. Its digest is bound in a second commit.

## Risks / Trade-offs

- A new release can change tool behaviour: `ty` moved three releases, `cyclopts` and `fastmcp` one
  minor version each, and Vale one. The full proof and hosted CI on both peers are the acceptance,
  and a regression is fixed or held in this Change with its reason.
- `min_version` 2026.11.8 refuses a host whose installed Mise is older. CI jobs install the bound
  executable by digest and do not depend on a runner's own Mise.
- The base image's pinned Debian package versions may be gone from the newer base; the image build
  names any that are.
