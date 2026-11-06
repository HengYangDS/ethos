# Design

## Context

See [proposal.md](proposal.md) and the reviewed design
`build/runtime/work/operator-verbs/cli-product-design.md`, sections 3 and 8.

- `EthosResult` in `src/ethos/result.py` is schema version 2, with a free-text `next_action` and a
  derived `continuation`.
- `apply_payload_budget` externalizes the whole result for `status` and `plan` only. It raises if
  the reduced result still exceeds the budget.
- `emit` in `src/ethos/surface/cli/output.py` applies the budget only when a command passes an
  artifact root.

## Goals / Non-Goals

Goals:

- An agent acts on any command's default result without a second read, and without parsing text
  to learn the effect or authority of the next step.
- No result can grow past its budget, and none can fail to render because of its size.

Non-goals:

- A new reader command. Detail stays in the existing digest-bound artifact. The command-plane rule
  "no alternate reader command" stands.
- A generic "run next" verb. It would let `--apply --authorize` slip past a harness's permission
  rules.

## Decisions

- **One budget rule for every command.** `PAYLOAD_BUDGETS` becomes a default of 16 KiB with
  per-command overrides. `emit` always applies it under the Git common directory, so callers no
  longer opt in.
- **What stays inline.** Externalizing keeps the wire fields and reduces `data` to three parts:
  - the command's own entries of at most 1 KiB, such as receipts, paths, digests and evidence
    references, because the next call binds to them;
  - `data.detail`, the digest-bound artifact of the full result;
  - `data.inline`: for each failing check, its id, exit code and first 20 output lines, with the
    omitted counts.

  If that is still too large, the failing steps, then the largest kept entries, then the gaps are
  truncated, with counts, never raising. `detail` and `inline` are reserved names: `prove` already
  emits `artifact_reference` for its evidence, and the bound must not replace it.

- **`next` derives from one owner.** Each command already computes `next_action` from its own
  facts. A small `NextStep` value object holds argv, effects, authorization and binding.
  `next_action` becomes its rendering for humans, so the two can never disagree. Commands that set
  only prose get `argv: null` and `authorization: human`.
- **Runtime identity.** It is read once per process from the running product's build identity, and
  placed in `summary.runtime`.
- **Schema 3.** `schema_version` becomes `Literal[3]`. `from_payload` refuses version 2, and the
  test runner and every internal reader move in the same commit.

## Risks / Trade-offs

- Every command that builds a continuation is touched. Mitigation: `NextStep` gets a constructor
  from today's command list, and the command-plane tests pin each command's next step.
- Some tests read the whole `data`. They read it through the runner's existing artifact expansion
  (`full_payload=True`, `result_data`).
