# Design

## Context

See the [proposal](proposal.md) and the [governance delta](specs/repository-governance/spec.md).

Read and measured on 2026-11-16:

- `_patch_references` in `src/ethos/adapters/admission/patch_admission.py` copies each preimage
  into a `tempfile.TemporaryDirectory`, calls `_patch_applies(workspace, patch)` and reads each
  postimage from the workspace. `_patch_applies` runs `git apply --whitespace=error-all -` with
  the workspace as its directory and returns whether Git exited with 0.
- Git's manual for `apply` states that from a subdirectory of a repository, patched paths outside
  that directory are ignored. Plain Git 2.56.1, run in a directory under an ignored directory of
  a repository, exits with 0 for a two-file move and changes no file.
- The product's Git runner drops every inherited `GIT_` variable except the identity ones, so a
  launcher cannot change Git's discovery from outside.
- The same module's check of the preimage runs `git apply --check` in the repository's root and
  is not affected. The admission of an index target reads the prospective index tree and uses no
  workspace.
- The undeclared-reference check and the deleted-input check have one caller, patch admission.
  The staged admission of a commit repeats the projection checks from the index tree, and does
  not repeat those two.
- Of the 32 places where the product creates a temporary directory, this is the one whose tests
  fail with the temporary directory inside a work tree, among the six admission modules run. One
  other place runs Git with a workspace as its directory, the carrier edit's
  `git diff --no-index`, and its module passes there.

Not run: the whole suite with the temporary directory inside a work tree, and a commit hook
after a wrongly admitted patch.

## Goals / Non-Goals

Goals:

- Patch admission reads the same postimage wherever the temporary directory lies.

Non-Goals:

- A rule on where a host may place its temporary directory.
- A change to the Git runner's environment for other callers.

## Decisions

1. **The workspace is a repository of its own.**
   - **Rests on:** two plain Git runs in one directory inside another repository's work tree,
     whose name held the separator of a path list: without a repository of its own Git exited
     with 0 and changed no file; after `git init` in the directory it applied the patch. The
     initialization took no time that the measurement shows.
   - **Considered:** a ceiling on Git's discovery at the workspace's parent, which was built
     first and which a path-list separator in the temporary directory's name defeats, with a
     wrong admission as before (measured); a comparison of each named path before and after
     the apply, built in three forms over three review parts, each of which refused a valid
     patch or admitted a wrong one, and which gave valid patches refusals that the release
     before did not have; a reader of patches in Python, which would repeat what Git owns; and
     another place for the workspace, which only moves the question.
   - **Chosen because:** it removes the cause and detects nothing. In its own repository no
     path of the patch lies outside, so Git skips none, and its exit status means what it means
     in a checkout. No valid patch is judged otherwise than before. The Git directory lies at
     the workspace's root, which no reader of the workspace walks: each reads the named paths
     or the tree of one Change.
   - **Applies to:** the apply in the workspace. The preimage check keeps running in the
     repository. A change that names a path under the Git directory is refused as a path that
     leaves the root; Git refuses such a path too. The workspace starts from no template, as
     the product's other repositories do: a host's template could set where the new
     repository's work tree lies (measured, review part 25).
2. **A patch that declares another kind of entry than a regular file is refused.**
   - **Rests on:** the model review: a new link is dangling in the workspace, its postimage
     reads as absent, and the patch is admitted without what the link names being read. The
     release before admitted it the same way.
   - **Considered:** reading what the link names, which the workspace does not hold;
     judging by what Git writes to disk, which is a plain file where Git is told not to make
     links; reading the modes from the patch's text, which three review parts showed to differ
     from Git's reading (where a header ends, what ends a line); and Git's summary of the
     patch, which names no mode for a `new mode` line without its pair and has no form for
     a program to read.
   - **Chosen because:** the admission judges text, and what it cannot read it does not admit.
     The mode that Git records for the entry decides, on every platform. The lead's rulings V
     and W of 2026-11-16 and 2026-11-17 hold it.
   - **Applies to:** every path that the patch changes in the workspace's index, by the fifth
     decision. A preimage that is a link is refused before it is copied. A repository adds a
     link through the worktree target without a patch, where the staged admission judges the
     index.
3. **The regression places the temporary directory inside another repository.**
   - **Rests on:** the measured pair of the proposal: one patch, refused outside and admitted
     inside.
   - **Considered:** a test of the helper alone, which would pin the helper and not the verdict
     that an adopter receives.
   - **Chosen because:** the public admission is what was wrong, and the test fails on the
     unchanged module. The workspace's own tests read four shapes of patch in a plain
     temporary directory, inside another checkout, and inside one whose name holds the
     separator.
   - **Applies to:** the worktree target of `lane prewrite --patch`.
4. **The class is swept once by the whole suite.**
   - **Rests on:** the six modules run so far, which are a sample.
   - **Considered:** reading each of the 32 places by hand, which finds what the reader thinks
     of.
   - **Chosen because:** the suite already states what each owner must answer, and one run with
     the temporary directory inside a work tree shows every owner that answers differently.
   - **Applies to:** this Change's last task. A failure in another owner is repaired here when
     it is this defect, and is otherwise carried to the draft `gate-environment`.
5. **What a patch does is observed in the workspace's own index, not read from its text.**
   - **Rests on:** four review parts in a row that each found a place where the product's own
     reading of a patch differed from Git's, and one measurement of 18 shapes of patch (edits,
     moves, copies, a file that becomes a directory, entries without content, links, a
     submodule, modes placed late or alone, text after an entry): after `git apply --index` in
     the workspace, Git's comparison of the index before and after named every changed path
     with its status and its mode, and Git itself refused the shapes that it cannot apply.
   - **Considered:** bounding each reading of the text as Git bounds it, which is a second
     reader of one format and was corrected again in each part; a walk of the workspace's
     files, which sees no submodule entry and sees a plain file for a link where Git is told
     to make none; and Git's summary (second decision).
   - **Chosen because:** one reader of the patch remains, and it is Git. The staged target
     already reads a patch's effects from the index without rename detection; both targets
     now state a creation, a deletion and a kind of file by the same reading. A Git step that
     fails in the workspace is a refusal.
   - **Applies to:** the effect at each named path, the refusal of a path that is no regular
     file, and a path that Git deleted without a change naming it, which is the source of a
     move and is read as deleted. The text is still read for two things: the place of each
     preimage, to copy it, where a wrong reading makes the apply fail; and the null target of
     a deletion, by the entry below. The reader takes each entry's path from Git and ends an
     entry's header where Git ends it. The request of a patch is held against the same
     record: it names every path that Git changed, a move's source among them, as the staged
     target has required in every release; a request for a move's target alone left the
     source's deletion unjudged and is refused (the lead's ruling X of 2026-11-17). The
     staged target holds its request against Git's comparison of the candidate index too, so
     a wrong reading of the text refuses on either target and admits on neither. Both
     targets read the record by one function, tree against tree, so that an entry that is
     only an intent to add and a submodule's configuration change nothing in it. A changed
     path that no change names and that Git did not delete is refused on both. One file is
     let be on both: the empty file that Git creates at the null path for a deletion without
     its mode line (the entry below); the same path with content is refused. The index's
     mode is the one reading of a path's kind: the workspace is a new directory of regular
     copies, so no separate look at the disk is kept (ruling Y).

## Risks / Trade-offs

- In a repository Git reads the attributes of the files it finds. The workspace holds the named
  files alone, so an attributes file counts only when the patch names it, with its content
  before the patch; the preimage check in the repository already reads the same file.
- A repository that added a link through a patch must add it through the worktree target.
- A deletion written without its `deleted file mode` line (`+++ /dev/null` under a `diff --git`
  line, as a plain unified diff has it) is read as a deletion of its preimage, as in every
  release. Git applies that entry as a move of the file to an empty file at `dev/null`
  (measured with Git 2.56.1), and neither target reads that file while it is empty. Whether
  the admission keeps this reading or refuses the form is a question for the cut of
  2026-11-19; a creation without its `new file mode` line is refused by Git already.
- Each admission of a patch starts four more Git processes in a repository of a few files.
