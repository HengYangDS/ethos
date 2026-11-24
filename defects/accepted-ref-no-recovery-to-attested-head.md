+++
title = "No operation restores an accepted ref to its last attested head"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "None inside ETHOS: the reference-transaction hook refuses every move of an accepted ref that is not a fast-forward to the candidate's head."
+++

When an unpublished local commit stands on an accepted ref that no closeout produced, ETHOS offers
no way back: a reset is refused with `accepted_ref_move_not_fast_forward`, a revert keeps the
commit in the accepted history, and `land` offers only forward moves. The last attested accepted
head is known from the closeout's effect Attestation. Found 2026-11-21 with the entry
`status-ready-on-unattested-accepted-head`.
