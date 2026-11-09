# Design

## Context

`version_text` renders from `version_result()`. `EthosResult` freezes its data, so
`result.data["identity"]` is a read-only mapping, and the check `isinstance(identity, dict)` is
false for it.

## Goals / Non-Goals

Goals: the human line carries the commit that the JSON projection carries.

Non-Goals: the JSON projection, which is correct; the line's other fields.

## Decisions

1. **Read the identity as a mapping.** The renderer accepts any `Mapping`, and a test pins the
   line's commit field to the first 12 characters of the JSON projection's `source_commit`.

## Risks / Trade-offs

- None beyond the line's format, which the scenario now states.
