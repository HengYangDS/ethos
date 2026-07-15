# Tasks

## Contract and implementation

- [x] Add an exact bootstrap state for one valid tracked legacy profile with a
  missing declaration.
- [x] Keep empty, malformed, untracked, widened, and multiple-Change profile
  writes blocked.
- [x] Document that the next write uses the existing Change-local scope
  companion bootstrap.

## Verification and closeout

- [x] Run focused tests, strict OpenSpec, lifecycle, claims, parity, and an
  executed HEAD-bound proof on the final committed head.
- [x] Archive only after the verification evidence is current; candidate
  landing, accepted-root closeout, local installation, GitLab publication, and
  GitHub mirroring remain separate transitions.
