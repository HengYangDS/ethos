# Design

## Context

`prewrite_guard` resolves the OpenSpec material scope from the working files at every moment.
The index-target preview builds a candidate tree and the commit has the index tree, yet neither
tree is read for OpenSpec. So one staged content gets different answers by where the working files
stand, and the accepted requirement's sentences on the preview and on the commit are not met.

## Goals / Non-Goals

**Goals:**

- The index-target preview and the commit give one answer for one staged tree.
- A staged tree that is whole passes whatever the working files hold.
- No admission that passes before this change is refused by it.

**Non-Goals:**

- Refusing a staged tree that cannot be observed, or one that fails beside whole working files.
  Both are reported here and armed by a later release.
- The preview without an index target, the worktree preview and a merge continuation.
- Which repository declaration the commit reads.

## Decisions

- **One function owns the staged scope.** `staged_tree_scope` takes the tree and the scope's
  evaluator. With no tree it returns the working files' answer. With a tree it evaluates a
  projection of that tree and lets that answer stand when it passes.
- **The projection is of the tree.** `openspec_tree_projection` checks out the tree's `openspec/`
  files, and the carriers that a report reads, into a temporary directory. Git, the Lease and
  history are still read at the lane. Paths in the answer are spelled against the lane's root.
- **Reporting first.** The obligation `staged-openspec-tree` is declared as reporting. While it
  reports, a staged answer that does not pass yields to the working files' answer, which carries
  the staged tree's gaps as reported. Armed, the staged tree alone decides.
- **A fault of the staged evaluation changes no verdict.** Every exception of the staged
  evaluation is caught and reported as `openspec_tree_projection_missing` with the fault's
  type. The fault's message is not kept, because it can name the projection. The release that
  arms the obligation narrows the catch and gives evaluation faults their own code.
- **The answer names its tree.** A pass decided by the tree carries `openspec.observed_tree`. An
  answer left to the working files carries none.
- **The hook says when it admits with a report.** One line on standard error names the reported
  gaps; the commit proceeds. The note is written to standard error's descriptor unbuffered;
  one that cannot be written refuses nothing, and a process without that stream writes none.

## Risks / Trade-offs

- A fault in the working files outside the commit no longer stops the commit. For a fault that
  Git cannot stage, such as an empty directory or an ignored file, which reader refuses it
  afterwards is measured before this Change is archived and stated in its tasks.
- Where the staged tree does not pass, the scope is evaluated twice: 0.44 s more at the hook and
  0.50 s at the preview for a landing of 20 paths.
- `prewrite.py` stands at the per-file ceiling of 500 effective lines.
- The reports of this obligation appear in a prewrite answer and in the hook's note. The audit
  does not count them, so the release that arms the obligation has no count to print yet.
