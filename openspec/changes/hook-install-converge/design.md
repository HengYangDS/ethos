# Design

## Context

See the [proposal](proposal.md). `install_hook_runtime` builds the result of `ethos hook install`
from the binding that `install_hook_launchers` returns, or from the refusal it raises, and
`EthosResult.next` derives the typed step from `next_action` through the catalog
(`src/ethos/result.py:116-121`). Hook activation also serves `lane start`, which carries the
binding as data, and `lane candidate`, which drops it; neither follows its continuation.

`ethos status` is the one hook-runtime inspection surface: `data.hook_runtime` carries the gaps and
the one repair command, bound to the root, the selected runtime and the right interpreter
(`src/ethos/adapters/repo/hook/observation.py:433-485`). After an activation that holds, that
binding has no gap, so status routes by the rest of the repository's state.

Measured at `23538df6b` in fixture repositories, with the result and its `next`:

- A first installation, and a second one that changes nothing: `pass`, `installed`, `done`. The
  status that follows names no installation.
- A repository with the self-hosted profile, its expected build stubbed, from the accepted root and
  from a linked worktree: `pass`, `installed`, `done`.
- Activated while a generation's removal fails, while the legacy locator is a directory, or while
  running processes are unreadable: `block`, `installed_cleanup_deferred` and
  `ethos hook install --json` without a root, a loop. The directory case returns the same result on
  a second run.
- Refused because the source environment is not lock-current, or because a linked worktree is
  unreadable: `block`, `blocked` and the refused request again, a loop.
- Refused because the state needs a reset, with or without `--reset-state`: `block`, `blocked` and
  the authorized reset, another request. The authorized reset then passes with `done`.

## Goals / Non-Goals

Goals:

- No installation result names, as `next`, the operation, root and request that produced it.
- A deferred or refused installation continues to the owner of the repair command.
- A guard that fails when a later edit brings the loop back.

Non-Goals:

- Moving reclamation out of the installation (Breaking (4) of the plan); decision 5 gives the
  evidence.
- The verdict, state, gap and exit of a deferred installation.
- Typed steps for status's repair command, which starts with an interpreter path and so reads as an
  instruction; and the catalog's tokenless exemption for `hook.install`.
- Loops in other builders.

## Decisions

1. **The builder owns the continuation.** Activation keeps the gap `hook_runtime_cleanup_deferred`
   and stops writing `next_action`, so one function names every continuation of the installation
   and none is written without a root.
2. **A deferral or a refusal continues to `ethos status --root <root> --json`.** Status re-observes
   the runtime. After an activation that holds it asks for no installation; after a refusal it
   names its one repair command. Alternatives: an empty `next` leaves a blocked result with no
   step; the `hook retire-supply` preview covers neither generations nor the locator today; a
   prose instruction gives up the executable step that a transient refusal needs.
3. **The verdict stays.** A deferred installation still reports `block`, the gap and exit 1, as the
   specifications and the reference say. Passing instead belongs with the move of decision 5,
   after which the installation has no reclamation to defer.
4. **A reset is named only to a request that is not that reset.** The two reset gaps continue to
   `--reset-state --authorize` unless the request already carried both, which then continues to
   status. No adapter path reaches that case today; the builder now cannot produce it.
5. **Breaking (4) is not part of this Change.** At `23538df6b` the installation still deletes: the
   legacy locator (`src/ethos/adapters/repo/hook/activation.py:116`, `:249`), unused generations
   and wheels (`:131-133`; `src/ethos/adapters/repo/runtime/retirement.py:321`, `:397`) and host
   installations that no recorded consumer needs (`:138`;
   `src/ethos/adapters/repo/runtime/materialization/host_retention.py:80`). `hook retire-supply`
   covers only installations pinned before consumers were recorded
   (`src/ethos/application/hook/installation.py`, `retire_host_supply`). The move needs a second
   plan and digest for generations, wheels, the locator and recorded installations, changes to
   about four specifications and to the tests that assert removal at installation in at least
   three modules, and a named Breaking change. An unmeasured estimate is at least +120 product and
   +300 test line-equivalents against this row's +30 and +120, so the move waits for the owner's
   decision.
6. **The guard.** `tests/unit/kernel/test_operation_catalog.py` gains one predicate, true when a
   result's `next` selects the producing operation with the same root and an equal request, and
   one table: four request forms against twelve classes of activation outcome, through the stubbed
   adapter. It also proves the predicate sees the base's continuation as a loop.

## Risks / Trade-offs

- A refusal that persists can become a cycle of two steps, when status names the installation and
  it refuses again. This is read from the routing, not measured, and the guard cannot see it.
  Ending it needs a typed instruction per refusal reason, which belongs with the plan's gap
  registry row.
- The guard reaches one builder through a stub. It cannot see a builder that needs a repository,
  prose that asks for the same run, or an argv that does not start with `ethos`.
- A deferred installation still exits 1 although its hooks are armed; a script that checks the exit
  alone still fails there.
- A reader that reran the installation on the old continuation runs status first. No argv, exit,
  verdict or wire field changes.
- The repository-governance scenario `Cleanup observation becomes unavailable` still says "a public
  recovery action"; status is that action, and the text is left as it is.
