# Design

## Context

See [proposal.md](proposal.md). The supply Dockerfile hashes eight owned inputs into the image's
manifest. The CUE image binding and the generated provider files are outside that manifest, so
replacing the digest does not create a digest cycle. The accepted `dev` and `main`, `80cce9529`,
carry the `0.2.0-alpha.19` inputs; the bound supply was published for `ad9108d70`.

## Goals / Non-Goals

**Goals:**

- GitLab jobs use a published supply whose complete input manifest matches the delivered checkout.

**Non-Goals:**

- Changing dependency versions, weakening checksum validation or extending product runtime
  behavior.
- Removing the need to rebuild the supply when a hashed input changes. That belongs to the bounded
  supply and state work.

## Decisions

- Use the native hosted `supply_image` workflow on the accepted `dev`. Its smoke stage checks the
  checkout offline as the same unprivileged user that runs GitLab jobs.
- Bind the inspected immutable digest through `.config/ci/pipeline.cue` and `ethos lane project`.
  Provider YAML remains generated output.
- Qualify the actual GitLab pipeline after publication. Local projection checks and the image smoke
  establish their own bounded claims.

## Risks / Trade-offs

- [A later change to any hashed input invalidates the binding] → Rebuild and qualify the supply for
  those inputs before advancing it. Each lock change still turns GitLab red until then; the bounded
  supply and state work owns removing that coupling.
- [Reverting only the image digest restores the detected mismatch] → Recovery selects a source
  revision and a supply whose inputs agree.
