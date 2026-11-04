# Design

## Context

See [proposal.md](proposal.md). The hosted `hosted_verification` session installs the core tools
first and then the remaining locked tools when a gate first needs them. Local hosts that ran
`mise install --locked` hold the whole supply, so no local test saw the difference.

## Goals / Non-Goals

Goals:

- Keep the refusal of a wrong tool, which the 11-04 experiment showed for aigw-cli's npm.
- Accept supply that is provisioned on first use.

Non-goals:

- Changing when CI installs tools.

## Decisions

1. Bind each check to the executable that a resolution returns. For `locked_tool`, the tool named
   after the requested executable must be installed, and the executable must lie inside one of its
   install paths. For `locked_environment`, each declared tool's own executable that resolves on
   the environment's mise PATH must lie inside that tool. When the tool is missing, the gap names
   it.
2. A declared tool whose executable resolves nowhere stays native mise's own outcome. A command
   that needs it fails with "not found", which cannot run the wrong tool.
3. `mise env` warns on stderr about a missing tool when another version of it is installed. Read
   `ls --current --json` before `env`, and name the missing tools with the step that can help when
   `env` fails.

## Risks / Trade-offs

- A declared tool that is missing and whose executable resolves nowhere is reported only when a
  command uses it. This is today's behavior, and the safe direction.
