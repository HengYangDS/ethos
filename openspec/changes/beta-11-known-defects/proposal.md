# Proposal

## Why

The entry of 0.2.0-beta.11 lists the release's known open defects. Three were found on
2026-11-16, after the release head was frozen and before its tag, and the entry holds none of
them. Each is in 0.2.0-beta.10 as well, so none came with this release.

- **Patch admission and the temporary directory.** `ethos lane prewrite --patch` applies a patch
  in a temporary workspace. When the process's temporary directory lies inside a Git work tree,
  Git skips every path of the patch there and reports success, and the admission judges the
  unchanged files. Measured on the installed 0.2.0-beta.9 and 0.2.0-beta.10 and on the source of
  the release head, with one patch and one repository: a patch that adds an undeclared
  executable is refused with the temporary directory outside every repository and admitted with
  it inside one, and the move of a dated Change is admitted outside and refused inside.
- **A full proof and the host queue.** A full proof that cannot open the host queue, take its
  place in it or give that place up raises the operating system's error itself. The review of
  the next batch found it in the code that both releases share.
- **A declared command gate and the launching shell.** A gate that a repository declares as a
  command receives the environment of the shell that launched the proof. Two full proofs of one
  governed repository, launched from a shell whose Mise activation variables had been removed
  while its `PATH` stayed activated, failed the same test under 0.2.0-beta.10 and under this
  release's packaged candidate; the proof passed from a clean environment. The entry's sentence
  on the repaired activation state says that every child starts without that state, which holds
  for the children of the providers and not for a declared command.

The owner decided on 2026-11-16 that the release head moves once more for the entry alone, so
that the release's own notes carry what is known before its tag. The decision named the first
two defects. The third is added on the same ground, after the pair of proofs verified it; it
corrects a sentence of the entry that says more than the release does.

## What Changes

- The entry's known open defects gain the three defects, each with its condition and with what
  to do until a release repairs it.
- The entry's sentence on the repaired activation state names the children that it covers.

Out of scope: any repair. The first two are repaired in the batch of 0.2.0-beta.12, and the
third is a case of the draft `gate-environment`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The Change corrects a release entry, so `skip_specs: true` applies.

## Impact

`CHANGELOG.md`, the entry of 0.2.0-beta.11. No product code, tool, test or configuration
changes: the release's notes change and its behavior does not. The release head moves, so its
hosted qualification, the release build and the build's install smoke run again at the new head
before the tag of 2026-11-21.
