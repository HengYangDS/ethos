+++
title = "A focused proof does not say that no gate ran, or reports evidence it never examined"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Pass `--expect-head`, or read the full proof."
+++

A focused proof, `ethos prove --execute --gate <ids>`, whose Commitment requires an axis that the
selection does not cover is refused before any gate runs, and its result does not say that no
selected gate ran. The refusal names the uncovered axis, `quality_obligation_unproven:<axis>`, not
a gate that would cover it, and its next action is the full proof. With `--host` and without
`--full` or `--expect-head` it binds no source tree and reports evidence as unproven that it never
examined. Pass `--expect-head`, or read the full proof.
