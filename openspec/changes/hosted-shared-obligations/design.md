# Design

## Context

`shared-quality-obligations` removed `product_source`, so ETHOS's own tree now receives the shared
floors that its authored carriers select, including the new `code-static` gate. Hosted run
40796064834 at `6186a48c4` exposed three defects that the lane's local proof could not see: the
workstation installs every declared mise tool, and no lane check selected a single gate on ETHOS's
own tree.

A local run reproduces the hosted failure. It prepares a fresh mise data directory and tool cache
as the hosted quality job does, then runs the `hosted_verification` session on `6186a48c4`.
`code-static` reports `mise_supply_unavailable:node`, and its sibling gates report
`process_cancelled` or `command_scope_cancelled`. With Node installed through mise in that data
directory, the `code-static` provider passes.

The three root causes:

1. **Focused code selection reads implementation locations.** `_owner_projection` in
   `repository/policy/gates.py` marks a focused selection as a code check when a selected gate
   verifies a code axis, declares a quality dimension, or reads a code subject as an input. The
   inputs are the gate's own provider module, native configuration, `noxfile.py` or script, never
   the subjects it checks. A tree that builds the product reads its providers from `src/ethos/`,
   which are code subjects, so the same selection of `external-links`, `docstrings` or `shell-lint`
   needs the code floor in ETHOS and not in another repository.
2. **One cancellation flag serves every nested scope.** `command_scope` reuses the enclosing
   `CommandScope` and cancels it when any exception leaves the nested scope, even when the caller
   handles that exception. `code_quality._report`, `verification.provider_reports` and
   `provenance.observation.integrity_report` all report provider failures as results after a
   nested scope has exited. One reported failure therefore cancels the proof's gate-graph scope,
   and every sibling gate fails at its next command creation with `process_cancelled`.
3. **CI supplies the declared Node outside mise.** `tools/ci/toolchain/native.py` installs cue,
   actionlint and Go through mise and materializes Node into ETHOS's tool cache.
   `code_quality._executable` resolves a mise-declared tool with `mise which`, so `code-static` on
   ETHOS's JavaScript finds no Node on a clean runner. The workstation hides this because its mise
   data directory holds every declared tool.

## Goals / Non-Goals

**Goals:**

- A focused selection compiles the same obligations for the same gates in every repository.
- A failure that a provider reports as its result never stops a sibling gate.
- The hosted quality job prepares every tool that the shared checks resolve through mise.

**Non-Goals:**

- Changing which tools a shared check resolves, or where. A repository's locked tool selection
  keeps owning its native checks.
- Rebuilding the GitLab supply image; that belongs to the supply work.

## Decisions

### Focused selection follows what the selected gates verify

`code_selected` keeps its first condition and drops the input condition. The inputs keep selecting
the source contracts whose members the gates read, so a focused native check still carries its
artifact-integrity duty. Focused evidence already cannot satisfy promotion, so dropping the input
condition removes no promotion guarantee.

### A command scope owns the commands started under it

`command_scope` opens a nested scope inside an enclosing one. Each scope holds its own cancellation
event and those of the scopes that enclose it, and one process-wide record maps each running
command to the events of the scope that started it. Cancelling a scope ends the commands whose
events include its own, and a scope refuses new commands once any of its events is set. A handled
failure in one provider thus ends that provider's commands, and an interrupted proof still ends
every worker's commands before the executor joins them.

Rejected: letting only the outermost scope cancel, because an exception in the runner's scope would
then wait for every running worker command before the thread pool joins; and a lock and registry
per outermost scope, which needs each nested scope to read its enclosing scope's private state.

### CI installs the declared Node through mise

When the configuration declares Node, `mise_tool_paths` adds `node` to the locked `mise install`
that already carries cue, actionlint and Go, and `require_cached_mise_tools` checks Node with cue
and actionlint in an immutable image. ETHOS's own Node supply in the tool cache is unchanged; it
serves the product runtime and npm.

Rejected: running the product-pinned ESLint on the product's Node. `static_observation` already
falls back to the product runtime, but the current contract is that a repository's locked tool
selection owns its native checks (`test_declared_mise_supply_precedes_ambient_path`). Changing it is
a separate decision, and the CI gap would remain for any other declared tool.

## Risks / Trade-offs

- **Late cleanup.** A command started under an exited nested scope stays in the process-wide record
  until its own release, so an enclosing cancellation still reaches it.
- **One lock per process.** Concurrent invocations in one process, such as MCP requests, share the
  lock that guards command creation. Creation is short, and a cancellation holds the lock for at
  most its termination grace.
- **GitLab.** The pinned supply image lacks mise's Node, so GitLab's offline preparation fails with
  `native_tool_offline_cache_missing:node` until the image is rebuilt; it already fails on its
  stale supply manifest.
- **Verification.** Focused regressions cover the focused composition of a script-implemented
  document gate, nested-scope ownership, and the offline and online Node supply.
  `prove --host --execute --gate external-links` on the lane must execute the gate, and the hosted
  quality job's preparation and proof, repeated on the lane head with a fresh mise data directory
  and tool cache, must pass every gate.
