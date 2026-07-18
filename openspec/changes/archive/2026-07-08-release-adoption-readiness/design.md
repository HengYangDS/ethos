# Design

## Boundary

This change is an evidence promotion only. It does not add a new release
mechanism, adoption profile, or command-plane behavior. It promotes bounded
command results from external pilot repositories and local release smoke checks
into tracked evidence.

## Evidence Model

The evidence chronicle records:

- product Git facts and command JSON summaries;
- external adoption pilot matrices for `generic`, `python`, and `gitlab`;
- GitLab conflict guard behavior for existing non-empty `.gitlab-ci.yml`;
- release artifact names, sizes, and SHA-256 digests;
- local-vs-remote-vs-hosted-CI boundaries.

Raw `/tmp` logs remain transient diagnostic material. The tracked chronicle and
claim manifest are the durable repository truth surfaces.

## Net Gain

The release/adoption readiness claim becomes reproducible enough for humans and
agents to audit without confusing local readiness with hosted publication or
hosted CI proof.
