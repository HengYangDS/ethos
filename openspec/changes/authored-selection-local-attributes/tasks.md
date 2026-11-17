# Tasks

## 1. The selection's reading

- [x] 1.1 Add the regression tests: a committed misspelling under a local mark, a tracked mark, a
      linked worktree, the case rule, a refused read and the text validity check. Done when the
      first, the second and the fifth fail at the release head for the stated reason.
      (With the release head's reading in the lane's selection, on 2026-11-18 under Python 3.14,
      eight cases of `tests/unit/adapters/gates/test_native_inputs.py` fail, these three among
      them.)
- [x] 1.2 Add `worktree_received_paths` and let `authored_source_files` read it. Done when the
      tests of 1.1 pass except the text validity check and the release's own test of received
      paths passes unedited.
      (`e9836b40a`; `tests/unit/adapters/repo/test_git_attributes.py` is as at the release head
      and passes.)
- [ ] 1.3 Give `authored_text_files` Git's own reading back. Done when every test of 1.1 passes.
- [x] 1.4 Read the marks against the tree that the source binding's owner builds from the head
      and the worktree's attribute files. Done when a committed misspelling blocks under a hidden
      attributes file beside it, a link in a parent directory reads no file outside, and an edit
      that an index flag hides counts and is seen by the binding. The first fails under the
      release head's reading and the second under the form that copied attribute files; the
      third holds the reading and the binding to one answer.
      (`3b092e238`; run on 2026-11-18 with each earlier form in the lane's tree.)
- [x] 1.5 List each pathspec, as bytes, before the owner adds it. Done when a tree without an
      attributes file marks nothing and refuses nothing, a new attributes file that Git would
      add counts, and an attributes file below a name that is not UTF-8 ends no selection; the
      first and the third fail without this task.
      (`8d6bbbf9f` and `2ee625582`, after the third and the fourth model review.)

## 2. The requirement

- [ ] 2.1 Modify the requirement on received paths to name the worktree's files, with one scenario
      for a local line. Done when strict OpenSpec validation of this Change passes.

## 3. Lane, hosted runs and the owner

- [ ] 3.1 Amend the Fixed item of the 0.2.0-beta.11 entry with the source that counts. Done when
      the changelog check reports nothing with 0.2.0-beta.11 as its release target.
- [ ] 3.2 Run `tests/unit/adapters/gates/test_native_inputs.py`,
      `tests/unit/adapters/repo/test_git_attributes.py`,
      `tests/unit/adapters/gates/test_source_format.py` and
      `tests/unit/adapters/gates/test_prose.py` on Python 3.12 and 3.13. Done when the four pass
      on each interpreter.
- [ ] 3.3 Read the Windows legs of the hosted host conformance at the lane head. Done when their
      install smoke, which runs the format command and a proof, passes on each leg.
- [x] 3.4 Run the release lead's probe of the gate's verdict against the lane head. Done when the
      prose gate blocks in its three states on both routes, the Git directory's attributes file
      and a hidden attributes file of the worktree.
      (At `d32673c8b` on 2026-11-18: block in the three states on both routes, the source bound
      each time.)
