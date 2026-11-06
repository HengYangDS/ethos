# Design

## Context

See [proposal.md](proposal.md). A bounded result keeps its wire fields, its own small `data`
entries and the scalar fields of a larger mapping. `required_gaps` may be shortened, and larger
entries move to the detail file that `bound.detail` names by path, digest and size.

## Goals / Non-Goals

Goals:

- Every ETHOS reader of another ETHOS process's JSON result judges the full result.
- A reader can expand a result that another runtime build wrote.

Non-goals:

- Any change to the bound, its budgets or the detail cache.
- Readers of other tools' JSON.

## Decisions

- **Expansion reads; it does not re-interpret.** `expand_result` keeps its checks: the detail's
  digest and size, a JSON object without its own `bound`, and agreement on every field the bound
  keeps. It returns that mapping. Validating it with the reader's own model adds only a dependency
  on the reader's vocabulary, which differs between builds whenever a result field changes, as
  `next-wire-shape` will change `next`.
- **Each reader keeps its own gap.** The probe reports `predecessor_policy_probe_invalid` and the
  candidate reader `candidate_semantic_runner_invalid`, as they do for any other unreadable result.
- **The inventory is complete in `src`.** A search for `ethos.cli` subprocesses whose stdout is
  parsed as JSON finds only these two readers. The other call sites build a command
  (`runtime/selection.py`, `hook/observation.py`), read `--version` text
  (`materialization/effect.py`) or re-execute the CLI (`cli.py`). In `tools`, the delivery
  acceptance reader and the hosted receipt already expand.

## Risks / Trade-offs

- A caller that relied on `expand_result` for model validation now validates the result itself.
  Only `tools/ci/delivery/acceptance/invocation.py` needs this, and it already does.
- `peer-resolution`'s rollback probe, which is not on dev, reads only `required_gaps`, which a bound
  may shorten. It adopts the same expansion when that lane is refreshed onto this one.
