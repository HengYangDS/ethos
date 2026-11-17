# Proposal

## Why

`ethos lane prewrite --target index --patch` refuses a patch that names exactly the requested
paths, with `prewrite_patch_paths_mismatch`, when a removed line of the patch begins with two
hyphens and a space. A governed repository's session reported it on 2026-11-15 from the released
0.2.0-beta.10, and the release lane reproduced it the same day with the function of its own head.

- The reader of a patch's paths, `unified_patch_changes`, takes the true paths from Git and then
  walks every line of the patch. Any line that starts with three hyphens and a space replaces the
  old path, and any line that starts with three plus signs and a space replaces the path, also
  inside a hunk.
- A unified diff writes a removed line whose content is `-- text` as three hyphens, a space and
  the text. On a patch that removes two SQL comment lines the reader returned the second
  comment's words as the old path. An added line whose content begins with two plus signs and a
  space gave its words as the path.
- Reach: every tracked language whose comments start with two hyphens, and Markdown or text lines
  that start so. One governed repository holds thousands of such lines.
- The enforcement point is not affected: the installed commit hooks judged the same staged tree
  and accepted it. Only the index pre-check refuses.

The release lead's ruling for the time until the fix ships: a session may stage such a patch with
Git after the worktree admission has passed for every path of it, and commit through the installed
hooks. That path bypasses no hook.

## What Changes

- The reader takes a file's old and new path only from the header of that file, between its
  `diff --git` line and its first hunk, or from Git's own summary of the patch.
- Regressions: a removed line and an added line that look like headers, a rename, a new file and
  a deleted file.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

One function of `adapters/repo/git_patch.py` and its tests. It narrows a refusal, which the law
freeze admits.

Repaired, and this draft is done: the row `postimage-workspace` of the batch that 0.2.0-beta.11
ships reads a patch's paths from Git and from each entry's header lines alone. A probe with a
removed line that begins with two hyphens and a space, and with an added line that begins with
two plus signs and a space, is refused at the release head of 2026-11-16 on both targets and
admitted at the lane head. The entry of 0.2.0-beta.11 names the repair under Fixed.

Owner: the release lead. Next action: remove this draft; no command retires a draft yet, since a
prewrite refuses the removal of a Change's own files. Read again: at the cut of 2026-11-26.
