# Design

## Context

The verifier judges each line a commit adds under an effective record root. Its malformed check
matched any run of letters, digits and dots before the marker's suffix, including an empty run,
so prose that names the suffix after a placeholder, or a code span that spells the form, refused.

## Goals / Non-Goals

Goals: refuse a broken attempt at a marker and admit text that only describes one.

Non-Goals: changing how markers pair, how unkeyed markers refuse, or what the record roots are.

## Decisions

1. **An attempted marker is hexadecimal.** The malformed check matches a run of one or more
   hexadecimal digits and dots before the suffix, in either case, and refuses it unless it is a
   whole marker. A placeholder's angle brackets or label names fall outside the run, and so does a
   suffix that no run precedes.

## Risks / Trade-offs

- A broken marker whose labels hold a non-hexadecimal character is no longer called malformed; it
  is also no marker, so the pairing check still refuses it if it replaced a peer's identity.
