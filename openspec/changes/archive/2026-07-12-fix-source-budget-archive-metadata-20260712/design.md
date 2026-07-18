# Design: classify archived OpenSpec headers as closeout metadata

## Context

The source-budget gate classifies every tracked YAML path as a maintained
carrier. An archived OpenSpec change is a historical closeout record, and its
required `.openspec.yaml` file contains only archive metadata. Treating this
exact path as executable source makes archival itself consume the YAML budget.

## Goals / Non-Goals

**Goals:** Keep the global source budget focused on maintained executable
carriers while preserving complete accounting for active OpenSpec metadata and
ordinary YAML configuration.

**Non-Goals:** Do not relax the budget for active specifications, archive
documents, arbitrary YAML, or any other extension category.

## Decisions

Classify a path as outside the source budget only when it starts with
`openspec/changes/archive/` and ends with `/.openspec.yaml`. The check runs
before generic suffix classification, so the normal YAML rule remains the
default for every other path.

The code-size correction compacts an existing immutable prune-set declaration.
It preserves the exact members and keeps the earlier Pixi traversal regression
as the behavioral proof.

## Risks / Trade-offs

- [An active carrier is hidden] → the rule requires the archive path prefix and
  exact metadata filename; active metadata continues through YAML accounting.
- [Archive documents disappear from governance] → the exception applies only to
  metadata; the archive validator and documentation surfaces still read all
  required closeout files.
