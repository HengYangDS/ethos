## Context

See [proposal.md](proposal.md). The `.claude/` entry dates from the July
decision that `.claude/skills` is a generated Claude Code adapter linked to the
tracked `.agents/skills` source; at that time Codex needed no root directory
because it reads `.agents/skills` natively. Agent sessions now also leave
host-local state, such as `.claude/.cc-writes`, at the roots of Work Lanes and
the accepted checkout.

## Goals / Non-Goals

**Goals:**

- Treat `.codex/` exactly like `.claude/`: host-local, never tracked, invisible
  to status and dirty provenance.

**Non-Goals:**

- Tracking agent host configuration, or changing `.agents/skills` as the shared
  Skill source.
- Changing proof gates. The generated-artifact topology governs root caches
  independently of Git ignore rules, and neither directory is a denied root
  cache today.

## Decisions

Use one repository ignore entry next to the existing one rather than relying on
a user's global excludes file, so every checkout, CI runner and agent observes
the same classification. Ignoring the directory instead of individual files
keeps future host state out of status without enumerating host internals.

## Risks / Trade-offs

- [A future Codex project file must be shared] → It would need an explicit
  tracked projection decision; this Change does not foreclose one.
