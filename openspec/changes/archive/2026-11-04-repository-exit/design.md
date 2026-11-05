# Design

## Context

See [proposal.md](proposal.md); the review conditions below are the durable copy of the
2026-11-04 design review. `install_hook_launchers` already reads `common_before`, and the worktree
values before activation, so that it can compensate a failed activation, and then it discards
them.

## Goals / Non-Goals

Goals:

- The configuration that install replaced is recoverable exactly, without a guess.
- An exit can be inspected with no effect, and its blockers are named.

Non-goals, for this slice: the apply, status reporting an exit, and reclaiming local generations.
A later Change delivers them under review conditions 3, 5 and 6.

## Decisions

1. **Public command.** `ethos adopt --exit` is the public exit. Adoption already owns runtime
   selection (`--select-runtime`), the exact-request flags and the plan digest, and the product
   design contract's lifecycle names exit beside adoption. A hidden `hook` operation would be
   limited to admission support. No PDC amendment is needed.
2. **Record location.** `<common>/ethos/hooks-preimage.json` sits beside the selectors.
   Retirement scans only digest-named generations under `runtime`, `hooks` and `packages`, so it
   never touches the record.
3. **When to record.** Install writes the record only when none exists and the current common
   `core.hooksPath` does not resolve under `<common>/ethos/hooks`: a first adoption, or a
   re-adoption after an exit. A record already present is never rewritten.
4. **Atomicity.** The record is written as a staged file inside `_activate_with_state`, after the
   activation succeeds and before the state transaction commits. A failure after that point
   removes a record written by this attempt.
5. **The preview is read-only.** It reads the config, the selectors, the record, the Lease rows
   through the read-only state URI, and the two locks by a non-blocking probe that releases at
   once. Its digest covers every value an apply would bind, including the Lease snapshot.

## Review Conditions

The review approved the exit with seven conditions, and the ETHOS session adopted them in full at
22:21. This slice delivers what a record and a preview can; a later Change delivers the rest.

1. Touch only ETHOS-owned values, and without a recorded preimage require the user's choice. The
   preview requires it; the apply must keep to it.
2. Record `common_before` and `worktrees_before` for all four keys in both scopes at install,
   atomically with activation, only when install replaces a value that ETHOS does not own.
   Delivered. The apply restores through `replace_config_values` and keeps
   `extensions.worktreeConfig` while any `config.worktree` has content.
3. Fence the apply's order under `runtime_selection_lock`: CAS the selectors and config, restore
   the config, verify that no worktree's hooks path resolves under `<common>/ethos/hooks`, then
   remove the selectors. Compensate exactly. Later Change.
4. Leave consumer records alone, because the host store owns them. The preview reports them as
   unchanged.
5. Reclaim the local `<common>/ethos/{runtime,hooks,packages}` generations inside the same fence,
   or name them as residue. Later Change.
6. Bind the apply to `--expect-plan` over the selectors, config, record and Lease snapshot, and let
   status report an exit as a fact. The plan digest binds those values; the flag and the status
   report are the later Change's.
7. Expose the exit publicly. Delivered as `ethos adopt --exit`, by decision 1.

The review also requires a refusal while a valid or unknown Lease, a held selection, a held proof
slot or a live process uses the runtime, and a list of unlanded branches in the preview. The
preview refuses on the first three; live-process detection and the unlanded-branch list remain
open. The apply writes a receipt before its effect, holding the selector bytes and hashes and the
configuration before and after, instead of a recovery directory. Re-adoption is a fresh
`hook install`.

## Risks / Trade-offs

- Repositories adopted before this release have no record. Their exit needs an explicit user
  choice, and the preview says so.
- A repository that ETHOS never adopted previews as unrecorded too; the apply must refuse it as
  not adopted rather than ask.
