# Design

## Context

`_observed_retained_origins` in the docs registry refuses an observation with gaps, a malformed
taxonomy, or an observation that differs from `retained_document_origins(root)`, and
`authored_document_paths` already leaves the registry's originals out of the authored inputs of docs
health, Prettier, prose and Vale. The paradigm report's `document_gaps` (front matter and decision
record names), `authored_name_gaps` and `_formatter_gaps` read every tracked path instead.

## Goals / Non-Goals

Goals: one verification of retained originals, read by every authored-document check, failing
closed.

Non-Goals: the observer and its byte and mode checks; the taxonomy grammar; any check that is not
about authored documents.

## Decisions

1. **The registry verifies.** `verified_originals(root, observation)` returns the declared paths
   when `_observed_retained_origins` accepts the observation, and an empty set when it raises,
   since its refusals are `ValueError`. The docs report keeps naming the refusal itself.
2. **The paradigm filters once.** `repository_paradigm_report` takes
   `retained_origins: DocumentOrigins | None`, computes `authored = tracked - verified` at its top,
   and passes `authored` to `document_gaps`, `authored_name_gaps` and `_formatter_gaps` only. A
   directory's name is judged from the authored paths, so a directory that holds only originals is
   not judged. The received paths stay as they are; no original is subtracted from them.
3. **Every caller passes the observation.** `governance_audit` forwards its `retained_origins`;
   `repair_paradigm` observes once with `observed_document_origins(repo)` and passes it to the
   plan's report and to the report after the apply.

## Risks / Trade-offs

- An original that is also an authored-looking path, such as a decision record name, is no longer
  checked by the paradigm; its bytes are the observer's to guard.
