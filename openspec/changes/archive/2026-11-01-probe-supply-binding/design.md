# Design

## Context

See [proposal.md](proposal.md). The supply Dockerfile hashes eight inputs into the image's manifest.
The CUE image binding and the generated provider files are outside it, so binding the digest does
not change the manifest. The workflow's offline smoke stage checked the image against the checkout
it was built from, including the Python and uv that Mise now declares.

## Goals / Non-Goals

**Goals:**

- GitLab runs the landed head with a supply whose input manifest matches it, and the shipped Python
  probe resolves its declared Python and uv from that supply offline.

**Non-Goals:**

- Changing any supply version, which `probe-supply` owns.
- Preparing a release entry; the next release collects these notes.

## Decisions

- **Bind the image that the hosted workflow built and inspected.** Its digest is read back from
  ghcr.io, and the GitLab supply jobs select it through the CUE owner and `lane project`.

## Risks / Trade-offs

- [GitLab still refuses the bound image] → The commit-policy job's manifest check names the
  differing input, and the image is rebuilt from the checkout that differs.
