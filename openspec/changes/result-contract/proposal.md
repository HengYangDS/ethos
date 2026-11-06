# Proposal

## Why

Agents are ETHOS's first user. The owner made agent-native design a mandatory product requirement
on 2026-11-06. Today the results that agents read are unbounded:

- A land result is about 385 KB, a closeout result about 778 KB and a release result about 1 MB.
  The median prewrite result is 94 KB.
- Only `status` and `plan` have a payload budget. When one of them overflows, ETHOS moves the
  whole result into a file. If even the reduced result is too large, it raises an error instead
  of returning one.
- `next_action` is one command string. An agent must take it, decide on its own whether it writes
  to a remote or needs a human, and run it. Every apply continuation already carries
  `--authorize`.
- Gaps are strings that pack their parameters into text, and there is no catalog of codes.
- A failing gate's evidence is either summarized away (prove keeps only a diagnostic count) or
  streamed to stderr without a bound.

This Change is the first slice of `agent-native-interface`
(`build/runtime/work/operator-verbs/cli-product-design.md`), which two reviewers accepted with
changes.

## What Changes

- **Every command's JSON result is bounded.** It has a declared default budget, 16 KiB unless a
  command declares less. Overflow never raises.
  - What stays inline: the verdict, state, gaps and continuation, the next step, and each failing
    step's id, exit code and first 20 output lines, with counts of what was omitted.
  - The rest moves into the existing digest-bound artifact, which the result names.
- **`next` is structured data.** It is `{argv, effects, authorization, binding, why}`, beside
  `next_action`, which is kept for humans and derived from the same value.
  - `effects` is one of `read`, `local-evidence-write`, `local-write`, `remote-read` or
    `remote-write`.
  - `authorization` is `embedded` or `human`.
  - `binding` holds the head, the plan digest, the receipt and the lease generation, each when
    present.
  - `argv` is null when a human must decide.
- **Every result names the runtime that produced it**: product version, source commit and runtime
  id.
- **The result schema becomes version 3.** Breaking changes are allowed, so there is no version-2
  reader.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: bounded results for every command, a structured next step, and runtime
  identity.

## Impact

- `src/ethos/result.py` and `src/ethos/surface/cli/output.py`, plus every command that builds a
  next action.
- `tests/support/ethos_cli_runner.py`, which already reads externalized detail.
- Every caller that reads `schema_version` 2. The Change moves them in the same commit.
- Out of scope:
  - the gap-code catalog and the exit-code contract, which are the next slice;
  - MCP parity, the command catalog and run handles, which are later slices.
