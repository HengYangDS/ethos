# Design

## Context

See the [proposal](proposal.md). The release binary scan reports binary advisories and never
blocks the release; the entry is where adopters read what remains open.

## Goals / Non-Goals

Goals: the entry names every advisory known for the bundled tools on the day of the release, and
its date is the tag's date.

Non-Goals: building CUE, Vale or shfmt in ETHOS with another Go toolchain, which would add a second
supply owner beside the official releases.

## Decisions

1. The advisory is a known open defect, not a blocker: ETHOS runs the three tools only as local
   commands over repository files and starts no HTTP server through them, and no fixed upstream
   release exists yet. A later supply move takes fixed releases once they meet the supply age rule.
2. The tag waits for 2026-11-12, so the entry's date is true by construction.

## Risks / Trade-offs

An adopter that runs these binaries as servers would be exposed; ETHOS ships them only for its own
gates, and the entry says so.
