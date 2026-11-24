+++
title = "An archived lane whose base moved is told to refresh; no refusal names the compensation that makes a conflict resolvable"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Return the unlanded archive first: `ethos lane archive-change --change <id> --expect-head <archive head> --compensate --json`, then its apply. Refresh the base with the merge strategy, resolve under the Change that is active again, and archive once more."
+++

A lane has archived its Change and has not landed. The accepted branch then moves, and the
refreshed base conflicts with a file of the lane. Two refusals follow, and neither names the way
out:

- `ethos land` (preview) at the archive head answers `block` with `candidate_base_stale`. Its next
  step is `ethos lane refresh-base --apply --authorize --expect-head <head> --json`. That is the
  rebase strategy, and the product aborts a rebase that conflicts.
- With the merge strategy started instead, `ethos lane prewrite <the conflicting file>` answers
  `block` with `openspec_material_path_uncovered:<file>`, and its next step is `openspec new change
<name>`. At an archived head no active Change covers the file, so the resolution cannot be
  admitted; a new Change is not what the lane needs.

The route that works is `ethos lane archive-change --compensate`, which returns the unlanded
archive to its head before the archive; the Change is active again, the merge's resolution is
admitted, and the lane archives again. The product offers that form only in the archive command's
own answers.

Measured in a governed repository's lane on 2026-11-23, 07:51 to 08:06, under the released
0.2.0-beta.11: the prewrite refusal during the
pending merge (07:51:56), the land preview's refusal (07:54:24), then the compensation's preview
(`pass`, `ready_to_compensate`) and apply (`pass`, `compensated`), the merge strategy with the
resolution admitted (`pass`, `base_merged`, then `base_current`). At the compensation both of its
published proposals stood two commits before the archive head; neither the archive head nor the
commit between them (a task tick, the head that the compensation returned to) was published. No
published proposal of the archive head is one of the compensation's conditions.

Read, not run, at `ca4a7fb62`: the guidance for `candidate_base_stale` is one fixed text
(`src/ethos/adapters/mutation/remediation/guidance.py`), with no case for an archived head, so the
landed head answers the same.
