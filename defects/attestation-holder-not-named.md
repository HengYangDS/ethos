+++
title = "No command says what still holds a proof or a landing record of a superseded head"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "List every ref, tag and worktree head at the commit, and each forge's last published refs there; retire or republish what still names it."
+++

A proof and the integration record of a head stay in the Attestation set while anything names
that commit: any ref of any tool, a peeled tag, a worktree's head, or a declared peer's latest
publication of a ref at that commit. No command reports which of these holds a record, so a
record that outlives its use cannot be traced to its holder.

Measured 2026-11-22 in ETHOS's own set by a read-only run: three proofs with their
integration records remain at superseded, untagged heads. Two pairs date from 2026-08-31 and are
held only by a proposal ref's last publication, which was never retired; one pair is held by a
snapshot ref that another tool wrote.
