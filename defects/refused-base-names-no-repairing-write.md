+++
title = "On a base whose OpenSpec tree is refused, no refusal names the write that repairs it"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Declare an unexpected TOML file with a patch whose only path is `.ethos/profile.toml` and which adds entries to `openspec.capability_metadata` or `openspec.specs_root_metadata`; create and complete the Change; move an unexpected Markdown entry of the specs root into the repository-local schema's `templates/`; repair each failing spec last; commit the whole in one commit."
+++

A lane is cut from an accepted branch whose `openspec/specs` holds files that the profile does
not declare, an unexpected entry at the specs root, or a spec that fails strict validation. Every
write is refused with the base's own gaps, and the next action is `ethos status` or
`openspec status`.

Writes that repair such a base are admitted, each under its own narrow scope, in one order: a
single-path profile patch that only adds metadata declarations (admitted with no Change and
while every other gap remains); the Change's metadata file, then its artifacts; one exact move of
a Markdown entry into the repository-local schema's templates (only under a complete Change, and
only where the repository has a local schema); a failing spec's file (only when failing specs
are the last gaps left). Deleting an unexpected entry has no admitted write while any gap
remains. No refusal names any of these, and none of them can be committed alone: the commit
admission admits them only together, in one commit that leaves the tree whole.

Measured 2026-11-22 in temporary fixtures with the source of `dev` at `024c217bf`. The
workaround was shown there as a sequence of admitted writes followed by one admitted commit; it
was not run on a governed repository.
