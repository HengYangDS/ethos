# Design

## Context

See [proposal.md](proposal.md). `expand_result` is the result contract's one reader for bounded
payloads; the delivery acceptance tooling already uses it (`invocation.py`).

## Goals / Non-Goals

Goals:

- The hosted receipt judges the same full result that the local proof produced.

Non-goals:

- Any change to the bound or to the receipt's rules.

## Decisions

- **Expand before judging.** The receipt expands the payload once, then applies every existing check
  to the full result. A detail file that is missing or does not match its digest refuses with the
  contract's own gap, which the receipt reports as an invalid observation.
- **The receipt's digest stays on the bytes the proof wrote,** so the evidence still names the
  exact file that the job uploads.

## Risks / Trade-offs

- The detail file must exist on the runner, which it does: the proof writes it into the job's own
  checkout store just before the receipt reads it.
