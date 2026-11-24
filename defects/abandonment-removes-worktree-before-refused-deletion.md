+++
title = "A lane abandonment removes the worktree before a deletion that the hook then refuses"
state = "closed"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Under 0.2.0-beta.11, do not abandon a lane whose proposal ref stands at a commit made before the adoption; retire it after the upgrade."
+++

In a repository adopted under a legacy branch-role table, the abandonment of a lane whose proposal
ref stands at a commit made before the adoption previews `derived`, removes the lane's worktree,
and the reference hook then refuses the ref's deletion: the repository stands in
`partial_transition`. The preview did not ask the hook's own deletion predicate, which only the
absorbed-ref retirement asked. Measured in a fixture on 2026-11-20. Repaired in the release after
0.2.0-beta.11: the abandonment asks that predicate before it persists an operation, and its apply
asks again before it removes anything.
