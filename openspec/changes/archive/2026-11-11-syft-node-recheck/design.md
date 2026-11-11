# Design

## Context

See the [proposal](proposal.md). Proof b9p1 of `supply-move-1112` stopped on this test alone: the
locked Syft read 1.57.1 against the pinned 1.57.0.

## Goals / Non-Goals

Goals: the pin names the locked Syft, after a recheck of its Node classification.

Non-Goals: removing the declaration path, which waits for a Syft that classifies `node.exe`.

## Decisions

1. The recheck reads Syft 1.57.1's release notes, which list seven dependency updates and three
   remediated advisories and no cataloger change. The declaration path therefore stays, and the
   pin moves to 1.57.1.

## Risks / Trade-offs

None: the test keeps its role for the next Syft move.
