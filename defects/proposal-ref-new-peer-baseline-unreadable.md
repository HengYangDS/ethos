+++
title = "A proposal ref for a peer with no accepted branch is refused without saying why"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Publishing the accepted branch to the new peer first, and fetching it, should avoid the refusal; that is read from the code and was not run."
+++

A proposal ref for a peer that has no accepted branch yet is refused with
`commit_range_trusted_baseline_unreadable:<ref>`, which does not say why. Publishing the accepted
branch to the new peer first, and fetching it, should avoid the refusal; that is read from the code
and was not run.
