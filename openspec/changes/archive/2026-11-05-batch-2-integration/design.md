# Design

## Context

See [proposal.md](proposal.md). `parameters.seconds(kind)` returns the invocation's declared
`timeout.<kind>_seconds`, or the paradigm default when no binding is active, as in a Nox session.
The defaults are `download` 180 s, `gate` 600 s and `request` 180 s.

## Goals / Non-Goals

Goals:

- `tools/` holds no more literal waits than the ratchet allows.
- DR-0018 has the five sections every decision record has.

Non-goals:

- Changing what the binary scan does.

## Decisions

- **The nearest declared kind.** The SBOM download is a download and the lock read is a request.
  The Grype scan, which may fetch its database first, takes the gate wait. That is 600 s by
  default, against the former literal of 1,800 s; a repository whose scan needs longer declares
  `timeout.gate_seconds`.
- **Evidence from the Changes that made the decision.** The new section points at the receipts
  Changes and their tests, and names when to revisit and retire the record.

## Risks / Trade-offs

- A Grype database fetch slower than 600 s now times out where 1,800 s would not. The release run's
  scan reports that as a timeout with its cause, and the declared parameter raises the wait without
  code.
