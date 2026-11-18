# Design

## Context

`docs/research/` holds studies as inputs: each states its sources, what was read and when, and
what was not reached. The earlier topics are the engineering foundations and the direction
carriers. A design that cites research cites a tracked study, so that its reasons can be read
again and checked.

## Goals / Non-Goals

Goals:

- Each claim of the studies names its source, and a reader can tell what was read from what was
  inferred.
- The rows that describe a forge's capabilities and plans are checked against that forge's own
  documentation by a reader other than their writer before they land.

Non-Goals:

- Any decision. What ETHOS takes from the studies is decided in its own records and Changes.
- A forge setting. The studies describe the two repositories' state as read; they change none.

## Decisions

1. **One topic, eight studies.** The questions share their sources (the forges' documentation,
   the same peer repositories), so one index serves them. Alternative, not taken: four topics,
   which would repeat the sources and split the reading that joins them.
2. **The state of ETHOS's own repositories is written as read on a day.** A row that says what
   ETHOS uses names the day and the collected answer it rests on. Such a row ages; the study
   says so in its head, and no gate reads it.
3. **The private forge is named by its kind and version only.** No address, namespace or
   identifier of it enters the text.

## Risks / Trade-offs

- A study of forge capabilities ages with the forges. It is dated, and a design that relies on
  a row reads the forge's page again.
- External links in research are checked by the link gate like any other; a source that moves
  is repaired where it is cited.
