+++
title = "After a Lease renewal, status reads a proven lane as ready and the landing refuses it"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Renew a lane's Lease before its proof, never between the proof and the landing, and take the landing preview, not `status`, as the reading of a proof."
+++

`ethos status` of a proven Work Lane reads `pass ready` with the next step `ethos land` after the
lane's Lease was renewed, while `ethos land` refuses the proof (`proof_lease_generation_stale`): a
proof is bound to its Lease generation, and the status reading does not ask the landing's own
admission. Met in one of ETHOS's own lanes on 2026-11-21: its Lease had been renewed after the
proof ended, and the landing preview refused the proof.

Until repaired: renew a lane's Lease before its proof, never between the proof and the landing, and
take the landing preview, not `status`, as the reading of a proof.
