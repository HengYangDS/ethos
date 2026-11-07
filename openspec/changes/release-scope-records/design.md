# Design

## Context

DR-0015 declared 0.2.0's journeys on macOS arm64, Linux x64 and arm64, and Windows x64
(`docs/decisions/dr-0015-release-stage-scope.md`, "For 0.2.0 the declared journeys"). The
2026-11-07 committee found that the Windows suite has never run in full and that the journey refuses
Windows, and the owner chose to narrow the declaration. The 0.3.0 channels decision of 2026-11-05 is
recorded only in session notes and in two drafts that planned a record number now taken.

## Goals / Non-Goals

Goals:

- Record both decisions where decisions live, with their alternatives and revisit conditions.
- Keep DR-0015's stage rules in force and supersede only its host list.

Non-Goals:

- Implementing the journey hosts, the Homebrew leg or the channels; their Changes cite these records.
- Choosing the 0.3.0 identity scheme or the channel carrier.

## Decisions

1. **A successor, not an edit.** Decision records are immutable once accepted, so DR-0021 states the
   narrowed scope and names what of DR-0015 it supersedes; the README marks DR-0015's host list as
   superseded.
2. **The channels record keeps the owner's words.** DR-0022 records the default identity
   `0.3.0-dev.N` that the owner named and notes that the change draft prefers another scheme; the
   implementing Change decides, against the version authority.

## Risks / Trade-offs

- Two records now carry the 0.2.0 scope until the distribution specification states the declared
  journeys itself; DR-0021 names that as its retirement condition.
