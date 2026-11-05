# Design

## Context

See [proposal.md](proposal.md). The changelog's historical entries record what was decided and
changed. They do not by themselves prove a tag or a published package. A correction is a new,
dated statement, not a rewrite of the entry's meaning.

## Goals / Non-Goals

Goals:

- Tell adopters that beta.1 has no release, and which version to take.

Non-goals:

- Deleting or moving the `v0.2.0-beta.1` tag on either peer.
- Republishing beta.1 under a risk acceptance.

## Decisions

- Add one dated note to the beta.1 entry. Keep its original text.
- State the upgrade path in beta.2's entry, alpha.30 to beta.2, so the release notes carry it.

## Risks / Trade-offs

- A tag without a release can confuse a reader who lists tags. The note, the GitHub release list
  and `ethos status` against the published releases all show which version is current.
