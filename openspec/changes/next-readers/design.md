# Design

## Context

`EthosResult` derives `next` from `next_action` (`src/ethos/result.py`, `contracts/next_step.py`):
an exact ETHOS argv becomes a `command`, or a `decision` when the result awaits a person; prose
becomes an `instruction`; `done` ends. The readers that still parse text:

- `tools/ci/delivery/acceptance/journey.py`, the status guidance to `lane candidate`;
- `tools/ci/delivery/acceptance/lane.py`, the prewrite continuation and the re-proof after a
  signed commit;
- `tools/ci/delivery/acceptance/merge.py`, the apply step after a merge preview.

Two more readers parse continuations nested in `data` (`runner_bootstrap` in `lane.py`,
`hook_runtime` in `runtime.py`), which producers do not type yet.
`tools/ci/delivery/distribution.py` checks that the damaged-supply recovery, a decision whose text
is a template with `<runtime-root>`, names `--runtime`; it reads guidance for a person and runs
nothing.

## Goals / Non-Goals

Goals:

- Every top-level continuation that an ETHOS-shipped reader follows comes from `next.argv`.
- The guidance agents read names `next` and the kinds they may act on.

Non-Goals:

- Typing nested continuations or converting producers; the catalog's `gap-codes` Change owns the
  remaining builders.
- Readers of predecessor releases, whose schema-2 results have no `next`.

## Decisions

1. **One helper, no fallback.** `continuation(result)` in
   `tools/ci/delivery/acceptance/invocation.py` returns `next.argv` for a `command` or a `decision`,
   whose argv these flows approve as the person, and nothing for an `instruction`, `done` or a
   missing step; each reader keeps its own refusal for an unexpected continuation. It never reads
   `next_action`, so a producer that stops typing a step fails the acceptance instead of being
   parsed. The `next` it reads is the reader's own derivation, which `EthosResult.from_payload`
   recomputes, never the carried one. A local-install-smoke run at 00:21:40 on 2026-11-08 showed why
   decisions count: the lease reacquire and merge previews await the person, and a helper limited to
   `command` returned nothing.
2. **Prose checks stay prose.** The distribution reader checks the wording of guidance for a person,
   so it keeps reading `next_action`.
3. **Guidance names the kinds.** The Skills and the quickstart say to run `next.argv` only for
   `command`, to ask the person for `decision`, to treat `instruction` as prose and to stop on
   `done`, and keep `next_action` as the rendering for people.

## Risks / Trade-offs

- The acceptance readers run inside `local-install-smoke` and the hosted package jobs; a mistyped
  producer now fails them. That is the intended exposure, and the full proof runs them locally.
