# Design

## Context

See [proposal.md](proposal.md). Two tests drive `sessions.secrets` with a stand-in Gitleaks:
`tests/architecture/test_nox_toolchain.py`, fixed with the seam change, and this one.

## Goals / Non-Goals

Goals:

- Every test that drives a session replaces the seam that the session calls.

Non-goals:

- Changing what the scan reads or reports.

## Decisions

- **Patch the seam, not the product function.** The session no longer calls `materialize_tool`
  directly, so replacing it there no longer reaches the session.

## Risks / Trade-offs

- None. An affected-module sweep over every test that imports a changed module runs before the
  next proof.
