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
  a repository, exits with 0 for a two-file move and changes no file. With
  `GIT_CEILING_DIRECTORIES` set to the directory's parent it applies the move.
- The product's Git runner drops every inherited `GIT_` variable except the identity ones, and
  adds what a caller passes. A launcher therefore cannot set the ceiling from outside.
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

1. **The workspace's apply runs under a ceiling at the workspace's parent.**
   - **Rests on:** the two plain Git runs above, and the runner's `env` parameter, which adds
     the variable to this one command.
   - **Considered:** initializing a repository in the workspace, which makes it its own top
     level, costs one more Git process for each admission and leaves a Git directory among the
     files that the postimage readers walk; a second reader of patches in Python, which would
     repeat what Git owns; and creating the workspace in another place, which only moves the
     question, because no directory of a host is known to lie outside every work tree.
   - **Chosen because:** it is Git's own control for where discovery stops, it changes one call,
     and outside a work tree the command runs as it did.
   - **Applies to:** the apply in the workspace. The preimage check keeps running in the
     repository, where discovery must find the repository.
2. **The regression places the temporary directory inside another repository.**
   - **Rests on:** the measured pair of the proposal: one patch, refused outside and admitted
     inside.
   - **Considered:** a test of `_patch_applies` alone, which would pin the helper and not the
     verdict that an adopter receives.
   - **Chosen because:** the public admission is what was wrong, and the test fails on the
     unchanged module.
   - **Applies to:** the worktree target of `lane prewrite --patch`.
3. **The class is swept once by the whole suite.**
   - **Rests on:** the six modules run so far, which are a sample.
   - **Considered:** reading each of the 32 places by hand, which finds what the reader thinks
     of.
   - **Chosen because:** the suite already states what each owner must answer, and one run with
     the temporary directory inside a work tree shows every owner that answers differently.
   - **Applies to:** this Change's last task. A failure in another owner is repaired here when
     it is this defect, and is otherwise carried to the draft `gate-environment`.

## Risks / Trade-offs

- On Windows a temporary path can be written in a short form. If Git does not match the ceiling
  to it, the command runs as before this Change: the repair is then absent there, and nothing
  is worse. The suite's Windows leg runs the regression.
- A later caller that applies a patch in a workspace of its own must pass the same ceiling. The
  helper takes it from its own directory, so a caller cannot forget it.
