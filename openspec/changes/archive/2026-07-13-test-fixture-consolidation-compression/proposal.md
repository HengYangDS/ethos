# Work-Lane Candidate Admission Matrix Compression

## Why

The Work-Lane start tests express three mutually exclusive candidate-readiness
states through nearly identical imperative test bodies. This duplicates setup,
invocation, and invariant assertions without adding independent behavior.

## What Changes

- Add the canonical quality requirement, then represent the finite candidate-readiness partition as one declarative pytest
  matrix.
- Preserve each state-specific setup and the required blocking gap.
- Delete the superseded test bodies; do not add a generic test DSL or change
  production lane-admission semantics.

## Out Of Scope

- Work-Lane runtime behavior, branch-role policy, CLI payloads, schemas,
  dependencies, and quality thresholds.

## Capabilities

- `quality`: subject=work-lane-candidate-admission-matrix-compression;
  reuse=extend; change=modify; facet:lifecycle=validation;
  facet:surface=test,openspec; facet:authority=source,test,openspec
