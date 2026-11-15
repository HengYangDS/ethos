# Proposal

## Why

An MCP client reads a step that it cannot follow as written. Since `environment-entry`, a result
that lacks an actor continues to the instruction `rerun the command with --actor <your own
identity>`. The prose names a CLI flag. An MCP tool takes no such flag: the server binds its
repository and its actor at startup, and the requirement `Installed MCP has bounded repository
authority` refuses a tool argument that would replace either. The client's real repair is to
start the server with the actor it should run as, and no part of the result says so.

The data is already there. The step's `inputs` hold one entry with the name `actor`, the flag
`--actor` and a description, and the operation behind the MCP `status` tool returns it. Only the
rendering is the CLI's.

## What Changes

Candidates for this row's design, none decided:

- The tool projection renders a step's `inputs` in the client's own terms: a value that a tool
  argument can carry as that argument, and a value that the server binds at startup as the
  startup binding with its repair.
- The step's prose stays the CLI's rendering, and the projection adds its own beside it; or the
  boundary that attaches the inputs learns its transport and renders one text for each.
- A regression that drives a missing-actor result through the MCP `status` tool and reads a step
  that the client can follow.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The MCP server's tool results and the step that a missing actor continues to. The CLI's results
keep their bytes.

Owner: the release lead. Next action: decide how a tool result carries a rendered input, with the
missing actor as its first case. Read again: at the cut of 0.2.0-beta.13.
