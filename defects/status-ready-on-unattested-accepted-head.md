+++
title = "`status` reports ready on an accepted head that no closeout attested"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Compare the accepted ref with the candidate ref by hand before publishing; `ethos publish` refuses the head with `accepted_closeout_effect_not_attested`."
+++

Git's client-side hooks are a convenience, not a barrier: an operation that bypasses them can
advance the accepted ref without the admission the hook performs. `ethos status` does not notice
such a head and reports the checkout ready with no gap; the unattested accepted head surfaces only
when publication refuses it.

The defect is the gap between the two moments, not the possibility of bypassing a client hook.
A repository that admits through the hook alone therefore has no early signal that its accepted
head was never attested. Found 2026-11-21 in a governed repository.
