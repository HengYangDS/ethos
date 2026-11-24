+++
title = "A repository whose hooks were armed before its accepted branch exists cannot create it, and no result says why"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Apply `ethos adopt --exit`, create the accepted branch and switch to it, run `ethos hook install`, then `ethos lane candidate`."
+++

A new adopter has one branch, its release branch. `ethos adopt` and `ethos hook install` succeed
there. With the hooks armed, the reference hook refuses the creation of the accepted branch with
`candidate_semantic_runner_unavailable` and of the candidate branch with
`candidate_ref_move_no_ref_intent`; `ethos status` blocks with `candidate_branch_missing` and an
empty next step, and `ethos lane candidate` blocks with
`candidate_bootstrap_requires_clean_accepted_root` and names `ethos status`. No result says that
the accepted branch must exist before the hooks are armed.

The three refusals close a circle: the accepted branch needs the candidate worktree's runner,
the candidate branch needs a product operation, and that operation needs the accepted root.
Nothing can be proven on such a root either (`ethos prove` blocks with
`openspec_active_change_missing`), and `ethos land --closeout` names as its next action an apply
that names the release head as both heads.

Reported 2026-11-21 from a governed repository. Reproduced 2026-11-22 in temporary fixtures, where
the workaround above ended at `status` ready; it was not run on that repository, where
the exit itself is blocked (see `adoption-exit-blocked-by-shared-installation`). Two
further findings of the same probe: the apply of `lane candidate` names the next step
`ethos lane start --help`, which selects no form, and `status` on the new accepted branch names
`lane candidate` while it lists the hooks as not armed.
