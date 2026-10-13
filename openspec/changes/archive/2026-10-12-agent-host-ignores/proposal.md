## Why

Agent hosts create host-local state directories at the repository root. Claude
Code sessions create `.claude/`, and Codex can create `.codex/`. Neither carries
repository authority. `.gitignore` covers `.claude/` but not `.codex/`, so
Codex host state would appear as untracked content in status and dirty
provenance and could be staged by accident.

## What Changes

- Ignore `.codex/` beside the existing `.claude/` entry in the repository
  `.gitignore`.

Out of scope: tracking any agent host configuration, adopter repositories'
own ignore files, the generated-artifact topology for root directories, and
where the Claude desktop app places its session worktrees.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Ignore rules for host-local agent state are repository configuration; no
specified ETHOS behavior changes.

## Impact

Only the repository `.gitignore`. No source, schema, dependency or tracked
agent projection changes.
