+++
title = "A closeout previews the rename of an old legacy role ref and its apply is refused"
state = "closed"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Run no closeout apply on a repository whose legacy role ref stands at a commit made before the commit that added the legacy table."
+++

A closeout previews `ready_to_rename` and its apply is refused (`git_effect_cas_rejected`) for a
legacy role ref that stands at a commit made before the commit that added the legacy table: the
hook's shape check reads the table at the deleted ref's own commit, the operation reads it at the
accepted head. Measured in a fixture on 2026-11-20. Repaired by the rename repair of the release
after 0.2.0-beta.11: the closeout renames such a ref. Under 0.2.0-beta.11, run no closeout apply
on such a repository.
