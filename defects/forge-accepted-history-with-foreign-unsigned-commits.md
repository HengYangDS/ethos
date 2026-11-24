+++
title = "A local accepted branch cannot catch up to forge history that holds unsigned commits"
state = "open"
since = "v0.2.0-beta.10"
fixed_in = ""
workaround = "none"
+++

A Work Lane cannot take the candidate of a repository whose forge `dev` holds commits that the
reference-update hook refuses, such as unsigned commits. The lane reaches that
history only through the local `dev` and the candidate: `ethos lane refresh-base --strategy merge
--source-ref` admits a Work Lane branch alone and answers `merge_source_ref_invalid` for a
remote-tracking ref, and the hook refuses the local `dev`'s catch-up for each such commit. No
command admits foreign accepted history, so the lane's full proof stays blocked. Do not re-create,
rewrite or re-sign that history.
