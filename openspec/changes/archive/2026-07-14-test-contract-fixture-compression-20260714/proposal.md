# Declarative CLI-Contract Fixture Compression

## Why

CLI lifecycle tests repeat the same adopted repository, candidate worktree,
owned Work Lane, and Git commit choreography; schema tests repeat a complete
workspace-status envelope already owned by the schema-sample module. The
repetition inflates test code without expressing new product behavior.

## What Changes

- Reuse a typed test-only fixture builder for the repeated adopted Work-Lane
  topology and committed fixture files.
- Reuse the canonical workspace-status schema sample for both acceptance and
  forbidden UI-projection cases.
- Preserve each named command, state, gap, and payload assertion; add no
  runtime abstraction or production dependency.

## Out Of Scope

- Lifecycle runtime behavior, CLI payload semantics, schemas, public APIs,
  dependencies, quality thresholds, and remote publication.

## Capabilities

- `quality`: subject=declarative-cli-contract-fixture-compression;
  reuse=extend; change=modify; facet:lifecycle=validation;
  facet:surface=test,openspec; facet:authority=source,test,openspec
