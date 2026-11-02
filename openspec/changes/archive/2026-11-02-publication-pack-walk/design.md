# Design

## Context

See [proposal.md](proposal.md). `run_network_git` removes every `GIT_CONFIG_*` overlay and
repository override so that no configuration can redirect the exact publication effect. That also
removes any way for a caller to choose Git's pack walk, and `pack.useSparse` defaults to true.

## Goals / Non-Goals

**Goals:**

- A publication push sends only the objects its peer lacks, also for a batch of renamed
  directories.

**Non-Goals:**

- Admitting other Git configuration through `run_network_git`, or changing the exact-lease
  refspecs, the atomic push or the pre-push admission.

## Decisions

- **One fixed option on the command, not an admitted overlay.** `-c pack.useSparse=false` before
  `push` changes only how the pack is computed; an overlay mechanism would reopen the redirection
  that `run_network_git` closes.

## Risks / Trade-offs

- [A push of a small change in a very large repository computes its pack more slowly] → The
  non-sparse walk is Git's long-standing default before 2.27; publication pushes are infrequent.
