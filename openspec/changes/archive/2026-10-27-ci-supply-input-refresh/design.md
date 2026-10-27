# Design

## Context

See [proposal.md](proposal.md). The supply Dockerfile hashes eight owned inputs. The CUE image binding and generated provider files are outside that manifest, so replacing the digest does not create a digest cycle.

## Goals / Non-Goals

**Goals:** use a published supply whose complete input manifest matches the delivered checkout.

**Non-Goals:** changing dependency versions, weakening checksum validation or extending product runtime behavior.

## Decisions

- Use the native hosted `supply_image` workflow. Its smoke stage checks the current checkout offline as the same unprivileged user that runs GitLab jobs.
- Bind the inspected immutable digest through `.config/ci/pipeline.cue` and `ethos lane project`. Provider YAML remains generated output.
- Qualify the actual GitLab pipeline after publication. Local projection checks and the image smoke establish their own bounded claims.

## Risks / Trade-offs

- A later change to any hashed input invalidates the binding. Rebuild and qualify supply for those inputs before advancing it.
- Reverting only the image digest would restore the detected mismatch. Recovery must select a source revision and supply whose inputs agree.
