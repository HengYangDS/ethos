# Design

## Context

See [proposal.md](proposal.md). Releases are admitted only after 24 hours, the age that Mise
enforces on its own tools. The GitLab supply image's manifest hashes both locks and the Mise
files, so any move needs a rebuilt image.

## Goals / Non-Goals

Goals:

- Every lock holds the newest stable release that has been public for at least 24 hours.

Non-goals:

- Moving mise itself. The host's mise is pinned until 2026-11-06 20:19 CST, and its owner lifts
  the pin.
- npm 12.2.x. Its patched bundles have not been released.

## Decisions

- **Native cutoff.** `uv lock --upgrade --exclude-newer` sets the age, and a plain `uv lock` drops
  the persisted option. Mise's own release-age rule admits only tools old enough.
- **Recheck `node.exe` with every new Syft.** The version pin test exists for this. It moves after
  the new Syft is run against a `node.exe` fixture.

## Risks / Trade-offs

- A new Syft could catalog other components differently. Each host-conformance leg's per-commit
  inventory step and the release-sbom gate check the inventories on every commit.
