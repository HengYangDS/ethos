# Design

## Context

See the [proposal](proposal.md). `_finish_report` in
`src/ethos/adapters/mutation/lane_lifecycle/handoff/transfer.py` builds one `MutationSubject` per
report, and the subject's `resource` must be non-empty. Export binds its required branch, import
falls back to the package path, and revoke passed the manifest's lane, which is empty when the
manifest is missing or unsafe.

## Goals / Non-Goals

Goals: every handoff report closes as a result that carries its gaps.

Non-Goals: mapping other validation errors to gap codes in general, which needs its own design.

## Decisions

1. Revoke uses import's rule: the subject is the manifest's lane, or the resolved package path when
   the manifest names none. One rule for both reports keeps one meaning of the subject.

## Risks / Trade-offs

None: only a report that already blocks changes its subject.
