# Tasks

## 1. The staged tree decides when it passes

- [x] 1.1 Judge the index-target preview and the commit by their staged tree. Done when a whole
      landing previewed against a refused base passes, the commit of the same index passes with the
      working files at that base, and both answers name the same tree. (At `e1bb11871`,
      `test_the_whole_landing_commits_from_the_index_alone` passes: the preview against the refused
      base passes, the commit of the same index passes with the working files at that base, and both
      answers carry the same `observed_tree`.)
- [x] 1.2 Keep every other answer. Done when the thirty-seven recorded cases show no pass that
      becomes a non-pass, and the worktree preview and a merge continuation project nothing. (At
      `e1bb11871` the probe ran the thirty-seven cases on the lane's code, each asked three ways
      (111 answers): no pass becomes a non-pass, 54 answers in 23 cases go from block to pass, no
      answer names the projection, and the preview and the commit agree in every case.
      `test_the_worktree_target_and_a_merge_continuation_read_the_working_files` passes and projects
      nothing.)
- [x] 1.3 Report and do not refuse. Done when a staged tree that fails beside whole working files,
      one that cannot be observed and one whose evaluation raises each pass with the gap reported,
      and an unobservable tree is refused once the obligation is armed in the test. (At `e1bb11871`
      three tests pass. A staged tree that fails beside whole working files passes with its gap
      reported and the hook's one note, and still passes when the note cannot be written. A tree
      that cannot be observed passes with `openspec_tree_projection_missing` and the fault's type
      reported, for an `OSError` and a `KeyError`, and is refused once the obligation is armed in
      the test. A `ValueError`, a `KeyError` and an `AttributeError` raised by the staged evaluation
      each pass with the fault's type reported and the projection removed.)
- [x] 1.4 Commit through the installed hook. Done when Git's own run of `pre-commit` admits the
      staged landing and the commit holds the staged tree. (At `e1bb11871`,
      `test_git_commits_the_landing_from_the_index_alone_through_the_installed_hook` passes: Git's
      own run of the installed `pre-commit` admits the staged landing and the commit holds the
      staged tree.)
- [x] 1.5 Name who refuses a working-file fault that Git cannot stage. Done when each of the
      measured cases names the reader that refuses it after this change, or says that none does.
      (Measured at `e1bb11871` on five cases, each committed with the fault left in the working
      files. An empty directory under `openspec/specs`, a specification marked skip-worktree and
      absent, an ignored entry at the specs root and a specification deleted and unstaged are each
      refused by `ethos status`, by the audit and by the full proof's context. An empty directory
      under `openspec/changes` is refused by `ethos status` and by the full proof's context; the
      audit passes it. With the fault taken out, status and the audit pass in all five.)

## 2. The record of the change

- [x] 2.1 State the change in the changelog. Done when the unreleased section names the staged
      tree's decision, the reporting obligation, the commit that now passes beside a working-file
      fault, and the two refusals that a later release arms. (The unreleased section's entry under
      Fixed names the staged tree's decision, the reporting obligation `staged-openspec-tree`, the
      commit that now passes beside a working-file fault, and the two refusals that a later release
      arms; Prettier and Vale pass on it.)
