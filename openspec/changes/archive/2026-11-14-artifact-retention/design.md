# Design

## Context

See the [proposal](proposal.md) and the [delta](specs/quality/spec.md).

- ETHOS's own pipelines compile from `.config/ci/pipeline.cue` alone. The common CI model,
  `.config/ci/verification.cue`, is packaged with the product and compiles only with a repository
  that declares it as `compiler.common`; ETHOS's own declaration does not. The two models are
  separate compilations, so no declaration in one is visible to the other.
- `pipeline.cue` gives seven GitHub steps an upload: the host conformance receipt, the proof
  receipt, the Python distributions, the external link observation, the release runtime of each
  platform, the release binary scan report and the release journey receipt. It gives three GitLab
  jobs an `artifacts` block: host conformance, verification and external links.
- The common model gives its GitHub verification job one upload step and each GitLab verification
  job one `artifacts` block. Its job definition is closed: compiling a repository model that adds
  `expire_in` to a generated job fails with a field that is not allowed.
- One step reads artifacts: `release-publish` uses `actions/download-artifact` with a `path` and
  nothing else, so it reads the artifacts of its own run, and it needs `release-platforms` of that
  run. A release run skips the per-push jobs, so the artifacts it downloads are the
  `release-runtime-<host>` uploads of its own platform legs, and the release assembler reads no
  other directory.
- No job downloads `python-distributions`, the proof receipt, a conformance receipt, the link
  observation, the scan report or a journey receipt. No tool under `tools/ci` or `src/ethos` calls
  a Forge for a run's artifacts: the binary scan and the journey read release assets and
  attestations, and the hosted observation reads a run's status.
- The GitLab model declares no `needs` and no `dependencies`, and every job that archives runs in
  the last stage, so no GitLab job receives another job's archive.

## Goals / Non-Goals

**Goals:**

- Every artifact that a hosted job of ETHOS keeps expires after 14 days, on both Forges.
- Every verification job that the common model generates carries the same retention.
- Each model declares the value once; no step repeats the number.

**Non-Goals:**

- Deleting artifacts that already exist. They keep the retention they were uploaded with.
- Log retention, release assets and attestations, which are not job artifacts.
- A retention parameter for a repository that compiles the common model.
- Jobs that a repository authors in its own model; the common model does not define them.

## Decisions

1. **One `let` per model.** `pipeline.cue` and the common model each declare
   `artifactRetentionDays = 14`. Each upload step's `with` reads it as `retention-days`, and each
   `artifacts` block interpolates it as `expire_in: "<days> days"`, so the number appears once in
   each model. One declaration for both models would need the compiler to pass a product input to
   both compilations, which is product code for one integer; two tests hold both models to 14.
2. **A reference in each carrier, not a pattern.** Each carrier names the declaration, as each job
   names its class in the timeout table. A constraint over every step that adds the key by
   construction was not tried; it would be a new kind of rule in this model. The architecture test
   reads both projections and refuses an upload step or an `artifacts` block without the value.
3. **The common model fixes the value.** It follows `GIT_DEPTH` and the source checkout retry: the
   generated job owns the field. Compiling a repository model that sets another `expire_in` on a
   generated job fails with conflicting values. A parameter with a default was the alternative; no
   repository asked for another value, and a parameter is a wider contract.
4. **The release uploads take the same 14 days.** Their one reader is a later job of the same run,
   so the retention only bounds how long after its platform legs a run's publication can be run
   again.

## Risks / Trade-offs

- A `release-publish` job that is run again more than 14 days after its run's platform legs finds
  no artifact, and the assembler refuses for a missing required platform. A new release run
  rebuilds them. The Forge's default bounded the same case before, at a longer time.
- A person who opens a run after 14 days finds its logs but not its receipts or reports. Hosted
  artifacts are host observations; the proof Attestation and Git history stay the record.
- Storage falls only as earlier artifacts reach the retention they were uploaded with.
- How each Forge treats the value at its limits was not read for this Change: what GitHub does
  with a `retention-days` above a repository's maximum, and whether a GitLab project keeps the
  archive of a ref's latest successful pipeline past `expire_in`. The hosted task reads the
  effective expiry back.
- The two models can drift apart in a later edit. Each has a test that names 14.
