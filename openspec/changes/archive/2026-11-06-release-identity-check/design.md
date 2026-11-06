# Design

## Context

See [proposal.md](proposal.md). Each release leg's
`build/evidence/local-install/release-smoke.json` records `source_commit` and
`distribution_version` beside the digests that the assembler already checks. The beta.3 uploads, for
example, record `df2dba636dc8…`, the tag's commit, and `0.2.0b3`.

## Goals / Non-Goals

Goals:

- Release assembly binds every published byte to the tagged commit and to the tag's version.

Non-goals:

- Re-verifying the tag's signature. Each release leg already admitted its build through the signed
  tag.

## Decisions

- **The head comes from the workflow.** The release run already carries `release_head`, and every
  leg verifies its checkout against it. The publish step passes the same input, so the assembler
  needs no Git access and stays standard-library only.
- **The version is derived, not passed.** The tag `vX.Y.Z-{alpha|beta|rc}.N` maps to the PEP 440
  `X.Y.Z{a|b|rc}N` that the build records. The assembler already requires the tag to have that
  shape.
- **One refusal per leg.** A mismatch names the host, as the other admission refusals do.

## Risks / Trade-offs

- Releasing a tag again from a newer main also passes `--expect-head`, which an assembler older than
  this Change rejects. Older tags are already published, and none is planned to be released again.
