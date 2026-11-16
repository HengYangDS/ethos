# Design

## Context

See the [proposal](proposal.md).

Read and measured on 2026-11-16:

- The patch admission module is the same file in 0.2.0-beta.10 and at the release head. One
  script ran the public admission with the temporary directory outside every repository and
  then inside an ignored directory of another one, on two installed releases and on the release
  head's source; the verdicts differ as the proposal states. Of 168 tests of six admission
  modules, 17 fail with the temporary directory inside a work tree.
- The host queue's defect is stated in the next batch's changelog, with the releases that hold
  it, and is repaired there.
- A gate that is a declared command is run with the process's environment, less two names of
  ETHOS's own; the code is the same in 0.2.0-beta.10 and at the release head. The children of
  the providers are built by the Mise adapter, which removes both families of Mise's
  variables in this release.
- The governing session's pair of full proofs of one tree, from the same launch environment:
  the packaged candidate and the released 0.2.0-beta.10 both stop at one test of a declared
  command gate, with the same six required gaps. The same tree's proof passes from a clean
  environment, as do the nine other readable repositories that take the release.

Not run: a commit hook after a wrongly admitted patch, and the first defect on Windows.

## Goals / Non-Goals

Goals:

- The entry of 0.2.0-beta.11 states each defect that is known before its tag, with a way to
  work until it is repaired.

Non-Goals:

- Any change of behavior in this release.
- A statement of the pre-tag copies run in the entry; its record is the release's own.

## Decisions

1. **The release head moves for the entry alone.**
   - **Rests on:** the owner's decision of 2026-11-16, and the release Change's rule that an
     entry lists the known open defects.
   - **Considered:** the tag at the frozen head with the defects on the weekly page and in the
     next entry, which costs nothing and leaves this release's own notes incomplete by what its
     lead knows; and a repair in this release, which changes product code five days before the
     tag and repeats every check and the copies run.
   - **Chosen because:** the product tree is unchanged, so the copies run's evidence holds, and
     a reader of this release finds its limits in its own entry.
   - **Applies to:** this release. A defect found after a tag is stated in the next entry.
2. **Each defect is stated by its condition, its effect and what to do, with no mechanism that
   was not read in the code or measured.**
   - **Rests on:** an earlier draft of this correction, which named a mechanism from three
     launch environments and was withdrawn the same day when the product's code showed another.
   - **Considered:** the measured versions and test names of the governed repository, which
     name an adopter's detail in a product's notes.
   - **Chosen because:** a reader acts on the condition and the workaround, and both were
     measured.
   - **Applies to:** the three bullets and the corrected sentence.
3. **The third defect is added though the decision named two.**
   - **Rests on:** the pair of proofs, which returned after the decision, and the code that both
     releases share.
   - **Considered:** leaving it to the weekly page, as planned before the head moved.
   - **Chosen because:** the head moves in any case, the entry's own sentence on the activation
     state says more than the release does, and the launch that fails is one that this
     project's own sessions used.
   - **Applies to:** one bullet and one sentence. The owner is told before the landing.

## Risks / Trade-offs

- The new head needs its qualification on both forges, the release build and its install smoke
  again; a failure there that the frozen head did not have would be a fault of the hosts, since
  no product file changes.
- The entry states the first defect from one platform's measurement.
