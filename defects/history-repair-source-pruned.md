+++
title = "A pruned history-repair source refuses later retirements"
state = "open"
since = "v0.2.0-beta.10"
fixed_in = ""
workaround = "Keep each history repair's old head under a ref (for example under refs/keep/) until every proposal ref that the repair rewrote is retired; the product reads that commit again at each such retirement."
+++

A completed history repair is verified again from its source commit whenever a later check asks
whether an older commit was absorbed, and nothing in the repository holds that commit: the repair
records a backup bundle, and Git prunes a commit that no ref reaches. Once the source is gone,
`ethos publish --retire` of a proposal ref whose head a base refresh rewrote is refused with
`signature_repair_source_coordinates_mismatch`, which names another cause, and the refresh evidence
that would answer is never asked. Measured on one repository with three repairs; 0.2.0-beta.10 reads
the same way.

Retire the proposal refs that a repair rewrote while the repair's source still exists, so that no
later retirement needs it; a source kept aside is absorbed or retired, not kept without an end.
With several repairs, one such retirement can take minutes.
