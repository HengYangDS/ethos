# Design

## Context

See [proposal.md](proposal.md).

- **Retention.** `retire_unused_installations` holds the host store's `install.lock` and, for each
  consumer record, acquires that consumer's selection lock without blocking before it reads the
  consumer's `CURRENT` and `ROLLBACK`. A held lock reports unknown liveness, so the record and the
  installation stay.
- **Lock acquisition creates.** filelock 4.2.4 creates the lock's parent directory before every
  acquisition and opens the lock file with `O_CREAT | O_EXCL` first. Opening an existing lock file
  writes nothing: it neither truncates nor creates.
- **Where a consumer's state comes from.** A repository's selection takes its lock, which creates
  `ethos/`, before its first pin records the repository as a consumer. A repository without `ethos/`
  therefore removed its ETHOS state after it pinned, or is another repository at the recorded path.

## Goals / Non-Goals

**Goals:**

- Retention creates nothing in a recorded repository that has no ETHOS state, and still releases its
  record.
- A repository with ETHOS state is observed exactly as before.

**Non-Goals:**

- Removing lock files that unreleased retention already created. Only unreleased heads ran it, and
  on this host every recorded consumer has ETHOS state (11 repositories, read on 2026-10-29), so it
  created none outside ETHOS state here.
- Changing how a selection takes its lock.

## Decisions

- **Guard on the `ethos/` directory.** Retention takes the consumer's selection lock only when
  `ethos/` is a directory. Without it, `CURRENT` and `ROLLBACK` are absent, so the consumer names
  nothing and its record is released. No selection can be about to name the installation: a
  selection that pinned it took its lock first, which would have created `ethos/`, and a new
  selection must pin again, which waits for the `install.lock` that retention holds.
- **Rejected: guarding on the lock file instead.** It would also leave an ETHOS repository that has
  never created its lock file untouched, but such a repository has selectors, and a restore or a
  selection transaction that changes them without pinning could then run between the existence check
  and the reads. With the directory guard, every repository that has selectors is read under its
  lock, and creating ETHOS's own lock file in ETHOS's own state stays within its ownership.
- **Rejected: a lock that never creates its directory.** A selection relies on the creation to hold
  its lock before its first record exists.

## Risks / Trade-offs

- [A selection creates `ethos/` between the check and the selector reads] → It cannot pin while
  retention holds `install.lock`, so it is not about to name an installation that retention is
  deciding; its selectors name nothing it has pinned yet.
- [`ethos/` is a symbolic link] → `is_dir()` follows it, so retention takes the lock through the
  link as before, and the selection checks keep refusing the link.
