# Design

## Context

See [proposal.md](proposal.md).

## Goals / Non-Goals

Goals:

- The binary scan passes repository hygiene and the type checker without a suppression.

Non-goals:

- Any change to the report's content.

## Decisions

- **A typed mapping.** `archives: dict[str, dict[str, object]]` is built in place and is the same
  object the report holds, so every write through it appears in the report.

## Risks / Trade-offs

- None found. The report's JSON is byte-identical, which the binary scan tests check.
