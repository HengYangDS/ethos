# Design

## Context

See the [proposal](proposal.md). The figures below were read at the base of this Change with
`git grep` over `src/ethos`, unless a decision names another command.

One module owns the actor: `src/ethos/adapters/actor.py` reads `ETHOS_ACTOR`, and 34 other modules
read it there on 52 lines. The actor is compared with the Lease's holder by equality and is no
credential. Three lines render `export ETHOS_ACTOR=<holder>` as a next action: two in the current
authority (`adapters/admission/current/authority.py`), for a missing and for a foreign actor, and
one in the linked retirement (`adapters/mutation/lane_retirement/linked.py`), for a foreign one. The
current authority's answer reaches at least five commands: one test reads it from `status`, `plan`,
`prove`, `lane prewrite` and `hook admit`.

The reader of `next.inputs` shipped first: `EthosResult.from_payload` keeps a carried step's
`inputs`, and no product module set them. An input is a `name`, a `flag` and a `description`.

Every catalog command already takes two options beside its request, `--root` and `--json`, which
`src/ethos/surface/cli/catalog.py` declares once. An explicit Change already binds one invocation
and its children through `ETHOS_CHANGE` (`selected_change`), and it is restored afterwards.

## Goals / Non-Goals

Goals:

- An executor names itself, and no result tells it to name another.
- A missing actor is asked for as data: an `instruction` whose `inputs` name the flag.
- A foreign actor is offered the native replacement of the holder, the handoff.
- A build one release older reads every new result.

Non-Goals:

- `binding.actor` in `next`, and typed steps from producers (appendix A.3; its rows convert the
  builders).
- `lease_actor_mismatch` at a landing, a release or a handoff. `lane-operations` owns those
  refusals.
- An `actor` input of the MCP tools, and a step rendered in an MCP client's terms. The server
  binds its actor at startup; the draft Change `mcp-step-inputs` carries the rendering
  (Decision 10).
- The Git configuration overlay, which the draft Change `gate-environment` carries (Decision 8).
- Continuations without `--holder-ref`, which the draft Change `lane-operations` carries
  (Decision 7).

## Decisions

1. **`--actor` is an option of every catalog command, not a request field.**
   - **Rests on:** the catalog, which holds 45 commands and 107 operations, none with an `actor`
     field (counted from `COMMANDS`, the catalog's table); and the five commands that return the
     same missing-actor refusal.
   - **Considered:** an `actor` field on the requests of the operations that read the actor, which
     costs a classification of 107 operations and a field in each request schema; and one option
     before the command word, which changes the shape of every rendered continuation.
   - **Chosen because:** the instruction says "rerun the command with `--actor`", and that holds
     only when every command that can return it takes the flag. The option sits beside `--root`
     and `--json` in one declaration. Accepted: a command that never reads the actor takes the
     flag and ignores it.
   - **Applies to:** catalog commands on the CLI and the `actor` argument of `invoke`. It does not
     cover `ethos host run` (Decision 9), `ethos mcp`, `--version` or help, and `--help --json`
     lists request fields only, so it names `--actor` no more than `--root`. The argv selection
     that `next`, the console and the command boundary share reads the flag on the same commands,
     so an argv that the CLI accepts selects the same operation on each of them.
2. **A given actor binds the invocation through the process input and ends with it.**
   - **Rests on:** the 52 reads of the one owner; the hooks that a commit starts and a detached
     run, which are child processes and read the variable; and the requirement
     `An explicit Change binds one invocation`, whose mechanism is the same.
   - **Considered:** a context variable that only `process_actor` reads, which a child process
     does not inherit, so a hook under a flag-named actor would see the fallback and refuse; and
     an `actor` parameter through the 34 modules.
   - **Chosen because:** one mechanism serves both explicit inputs. `process_input` in the process
     adapter sets one input for an invocation and restores it, `selected_change` now calls it, and
     `invocation_actor` calls it with the stripped actor. Accepted: the input is process-wide
     while the invocation runs, as the Change selection already is.
   - **Applies to:** one invocation and the children it starts. A blank value is no actor. The
     value's form is not checked here: the comparison with the Lease's holder decides.
3. **`--actor` wins over `ETHOS_ACTOR`, and a difference refuses nothing.**
   - **Rests on:** appendix A.7, which orders the two sources, and this row's rule that no refusal
     is added beyond the named Breaking entry.
   - **Considered:** refusing when both are set and differ, which would refuse every harness that
     exports the variable and then follows a step that names the flag.
   - **Chosen because:** the flag is the more specific statement of one invocation. Accepted: a
     stale variable is overridden without a notice.
   - **Applies to:** every catalog command. The MCP server still refuses a variable that changes
     under it.
4. **A missing actor's step is one prose text, and the invocation names its input.**
   - **Rests on:** `derive_next_step`, which makes prose an `instruction`; the two producers of the
     gap `invocation_actor_missing` (the current authority and the retirement's holder check); and
     the 47 constructions of a result in 22 modules, with four readers of the resolution's next
     action between the authority and its commands.
   - **Considered:** carrying the inputs through every builder, which touches the resolution, its
     four readers and the lane projection; deriving the step from the first gap at the boundary,
     which overrides what a builder rendered and leaves a nested copy of the old text; and an
     argv with a placeholder, which the producer cannot render because it does not know the
     command that called it.
   - **Chosen because:** the text has one owner, `ACTOR_STEP`, and the boundary that every
     transport shares attaches the input when a result's next action is that text, so the text
     and the data cannot disagree and nothing is overridden. Accepted: a producer that reports the
     gap with another next action carries no input. Both producers have a regression.
   - **Applies to:** every result that `invoke` returns, for the CLI, the SDK and MCP.
5. **The input and the option are one object.**
   - **Rests on:** the reader's design, where an input is a name, a flag and a description, and
     its risk that a producer could name a flag which selects an operation.
   - **Considered:** a literal in the result and another in the CLI, which can drift.
   - **Chosen because:** `ACTOR_INPUT` holds `actor`, `--actor` and the help text, the CLI declares
     its option from it, and a test holds that no request has an `actor` field, so the flag
     selects no operation.
   - **Applies to:** the one input that this Change produces. A later input needs its own rule for
     where its three members come from.
6. **A foreign actor continues to the handoff preview, as a decision.**
   - **Rests on:** the request of `lane handoff transfer`, whose five required fields the Lease
     and the actor supply; its preview, which checks the holder only on apply
     (`adapters/mutation/lane_lifecycle/lease/operation.py`); and a test that runs the rendered
     argv and reads a passing preview.
   - **Considered:** the apply, which only the holder can run and which would refuse the executor
     with `lease_actor_mismatch`; `lane lease takeover`, which needs an accepted Attestation and
     the source's end state, neither of which the refusal knows; and the lane's status, which
     names no step.
   - **Chosen because:** the preview is read-only, anyone may run it, and it carries the exact
     generation that the holder then applies. The step keeps `user_decision_required`, so it is a
     `decision` that a person takes to the holder. A missing Lease still continues to
     `lane lease reacquire`, as before.
   - **Applies to:** `lease_holder_mismatch` from the current authority and
     `foreign_work_lane_retire_authority_required` from a linked retirement, each with a valid
     Lease. The step is rooted at the lane, where the transfer runs. A Lease whose generation,
     expiry or holder cannot be read names nothing to move, so its step is the lane's status.
7. **Continuations keep `--holder-ref` here, and `lane-operations` removes it.**
   - **Rests on:** five lines in four modules that render the flag, and the requests of
     `lane start`, `lane lease reacquire` and `lane handoff transfer`, where the field is
     required. The scope plan names only the actor export as this batch's Breaking entry.
   - **Considered:** making the holder default to the actor in those requests now, which changes
     three request contracts that `lane-operations` redesigns.
   - **Chosen because:** the handoff needs both holders by name, the other steps name the executor
     itself, which is no impersonation, and one Change should own the holder of a lane verb.
     Accepted: appendix A.9's item on `--holder-ref` waits for that Change.
   - **Applies to:** every continuation of this build. The draft Change `lane-operations` carries
     the removal, and its proposal names it.
8. **The Git configuration overlay leaves this Change, and `gate-environment` carries it.**
   - **Rests on:** what the suite's own overlay carries. `tests/support/git_isolation.py` and
     `tests/conftest.py` give it `core.fsmonitor`, `maintenance.auto` and, for each test,
     `init.templateDir`, and `tests/support/ethos_cli_runner.py` keeps the first two for every
     in-process run. Further: 354 lines in 104 modules call local or network Git, and
     `adapters/repo/git.py` holds 490 of its 500 effective lines by the source budget's measure.
     Network Git already drops the overlay, and a `safe.directory` of `*` already refuses.
   - **Considered:** admitting only `safe.directory` now, after which every in-process result of
     the suite names two dropped keys and product Git in tests loses its isolation; declaring the
     suite's keys as well, which admits a key that can name a program and so needs a rule for
     values; and naming undeclared keys for one release before dropping them.
   - **Chosen because:** which keys and values the declaration admits is a design of its own, each
     choice changes the environment of every Git call, and `gate-environment` owns the neighbouring
     environment of gate children. One declaration serves both.
   - **Applies to:** the second sentence of appendix A.7: declared keys, dropped keys in
     `summary.environment`, and no overlay for signing. The draft Change `gate-environment` carries
     it as an obligation, and its proposal names it.
9. **`ethos host run` takes no `--actor`, so the child keeps its own.**
   - **Rests on:** a parse of six argument forms at the base and with the option added, without
     running a command. At the base a flag that `host run` does not declare reaches the child with
     or without `--`, while `--json` and `--root` are read by ETHOS when no `--` precedes them.
     With the option on every command, `host run <command> --actor x` gave `x` to ETHOS and the
     child lost both words.
   - **Considered:** naming that as a second Breaking entry with the repair `--`, which leaves a
     silent case where a child's argument becomes the actor on the host's ticket; and reading the
     option only before the command's first word, which needs a parser of its own.
   - **Chosen because:** the six forms then parse as they did at the base, so nothing breaks, and
     `host run` reads the actor only as the owner of its ticket and never returns the step that
     asks for one. Accepted: for this command the actor comes from `ETHOS_ACTOR` alone.
   - **Applies to:** every command whose operation exits as its child does, which is one command
     today. The rule is read from that declared exit kind, not from the command's name, by one
     function that the CLI and the argv selection both call.
10. **The step's `inputs` are what a tool projection reads; rendering them is another Change.**
    - **Rests on:** `src/ethos/surface/mcp/server.py`, which binds the actor at startup and whose
      `status` tool calls the operation that a test reads the input entry from; and the
      requirement `Installed MCP has bounded repository authority`, which refuses a tool argument
      that replaces the binding.
    - **Considered:** an `actor` argument on the tools, which that requirement forbids; and a
      second text for MCP from the boundary that attaches the inputs, which would have to know its
      transport.
    - **Chosen because:** the entry of name, flag and description is the same for every transport,
      and the prose is the CLI's rendering of it. Accepted: until the other Change lands, an MCP
      client reads prose that it cannot follow as written.
    - **Applies to:** every result that carries the input. The draft Change `mcp-step-inputs`
      carries the rendering for a tool client.

## Risks / Trade-offs

- A caller that ran or matched the `export` line stops working. The changelog names the repair,
  and the result's data still holds the Lease's holder.
- `--actor` is as unauthenticated as the variable was. It makes naming oneself easy, and no step
  suggests another's name any more, but nothing stops a caller that passes one.
- The preview of a handoff passes for an executor that is not the holder, and its own next step is
  the lane's status. An agent that ignores a `decision` would move between the two. The kind
  `decision` and its `human` authorization are what stop it.
- Over MCP the instruction names a flag that a tool call cannot take. There the repair is to start
  the server with `ETHOS_ACTOR` set, and the step does not say so until `mcp-step-inputs` lands.
- A second command that hands its words to a child must declare the same exit kind, or it takes
  the option and reads the child's flag.
- An actor passed as a flag shows in the process list, as `--holder-ref` does. It is an identity
  and no secret.
- The process input is shared by every thread of the process while an invocation runs.
