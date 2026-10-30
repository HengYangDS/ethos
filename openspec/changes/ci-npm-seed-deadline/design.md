# Design

## Context

See [proposal.md](proposal.md). `tools/ci/toolchain/npm.py` runs npm from the locked Node supply
for every hosted job and every release runtime leg, with one deadline for the whole command.

## Goals / Non-Goals

**Goals:**

- A deadline above the duration that every supported host leg observes, with margin, so a
  slow but healthy seed completes.

**Non-Goals:**

- Faster seeding, such as an npm cache for the emulated leg.
- The other Windows and load-sensitive failures seen on 2026-10-30; each gets its own Change.

## Decisions

- **One deadline for every host.** A per-host deadline would add a host table for one value; the
  bound exists to end a hung process, not to pace healthy ones.
- **600 seconds.** About five times the emulated leg's 108-second success, and well under the
  jobs' own timeouts, so a hung npm still ends inside the job.

## Risks / Trade-offs

- [A hung npm now holds a job for up to 10 minutes instead of 2] → The job still ends with a
  named timeout well inside its own limit.
