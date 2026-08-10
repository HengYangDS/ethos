# Design

## Context

An OpenSpec Change moves from `openspec/changes/<id>` to a dated archive path.
Architecture claims that concern the Change's retained semantics must therefore
bind to `commitment.toml` identity, not to its lifecycle-dependent directory.
Claims about current mutable OpenSpec material must instead enumerate active
Change directories.

## Decision

Keep both ownership rules explicit:

1. terminal historical assertions find exactly one carrier whose Commitment ID
   is `change:terminal-convergence`;
2. current-format assertions enumerate only direct active Change task files.

Missing or duplicate terminal identities remain assertion failures. No fallback
path or archived-mutation authority is introduced.

For destructive Git effects, readiness is not a weaker projection than apply.
The public command compiles one exact `TransitionPlan`, admits its permission
and prestate without mutation, and reports that plan in dry-run. Apply executes
the same plan shape after immediate drift checks. Absorbed-ref authority is
narrowly bound to `lane.retire`, one `work/*` deletion, an absent Lease and
worktree binding, and the asserted accepted ancestor; it is not generic CAS.
