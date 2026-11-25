+++
title = "A staged tree that fails OpenSpec is reported, not refused, until the obligation is armed"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Read `reported_gaps` in the answer of the index-target prewrite preview before the commit and repair what it names; a tree it names is refused once the obligation is armed."
+++

The accepted requirement "Exact Index-target Prewrite Admission" says that the index-target
preview evaluates the patch independently of working-file bytes. Through 0.2.0-beta.11 that
preview, the worktree-target preview of a patch and the commit hook's own admission took every
OpenSpec observation from the working files instead of from the tree the commit would carry.

Three consequences were measured in temporary fixtures on 2026-11-22: a patch whose own tree is
whole was refused while the working files held nothing of it; a patch that breaks the specs root
was admitted when the working files were whole; and a commit that staged a Change alone was
admitted under an unstaged working profile. In each case the tree that would be committed and the
tree that was judged differed.

What 0.2.0-beta.12 changes: the index-target preview and the commit's admission evaluate a
projection of the staged tree, and its answer stands when it passes. That repairs the first
consequence at those two moments. For the second and the third, the obligation
`staged-openspec-tree` enters as reporting: a staged tree that does not pass, that cannot be
observed or whose evaluation fails leaves the verdict to the working files, as before, and its
gaps are returned as `reported_gaps`. A later release arms the obligation; such a tree is then
refused. The preview without an index target, the worktree-target preview and a merge
continuation are unchanged.

Reported for the first consequence on 2026-11-21 from a governed repository whose landing lane
holds its content as one patch of 6,271 paths.
