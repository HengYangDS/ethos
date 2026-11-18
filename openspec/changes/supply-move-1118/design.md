# Design

## Context

See the [proposal](proposal.md). The rule that blocks here asks one question of a locked npm
artifact that an advisory names: is the artifact, or the package that bundles it, its registry's
latest release. A new release of the bundling package turns its bundled findings from reported
to blocking, whether or not the new release changes them. The same happened on 2026-11-05 with
npm 12.2.2, which did repair six advisories.

## Goals / Non-Goals

Goals:

- A head of this lane passes its proof again, by the path that the requirement names first.
- The lock moves npm and its bundled packages alone.

Non-Goals:

- The rule's gap: a finding behind the latest release blocks although the latest release holds
  it too. It is the subject of the draft `audit-latest-named`, which gains this case.
- A whole supply move, and any other pin.
- A disposition for the three bundled findings. Whether the owner accepts them for a limited
  time, so that a later npm release before the tag does not block again, is the owner's
  decision and is asked on a page; this Change does not depend on the answer.

## Decisions

1. **npm moves alone.**
   - **Rests on:** the audit's own record of the stopped proof, whose three unapproved subjects
     all lie in `node_modules/npm/node_modules/`, and the registry's publication time of npm
     12.2.3.
   - **Considered:** a whole supply move, which changes more of a release head three days before
     its tag than the block asks for; three dispositions without a move, which accept a risk
     where an upgrade exists and leave the entry naming a release that is no longer the latest.
   - **Chosen because:** the smallest change that the requirement's first path allows. The
     precedent is the Change `npm-advisory-move` of 2026-11-05.
   - **Applies to:** `package.json` and `package-lock.json`.
2. **The lock is resolved again by a whole install without scripts, outside the lane.**
   - **Rests on:** the measurement of 2026-11-12: once a direct pin changes, a resolution of the
     lock alone drops the bundled entries of the npm dependency, and a whole install in a
     directory that holds only the two files keeps them. Here: 555 entries before and after,
     nine entries changed, each `resolved` address the public registry.
   - **Considered:** a resolution of the lock alone, which npm refuses for the bundling
     package's archive under its default for remote archives, and which dropped entries before.
   - **Chosen because:** it is the one way that was measured to keep the lock whole.
   - **Applies to:** how the lock was made; the lane receives the two files.
3. **The disposition names the new lock's digest.**
   - **Rests on:** the owner's acceptance of 2026-11-18 for picomatch 2.3.2 in this
     repository's own lock, and the record's binding to that lock's digest, which a test holds
     against the committed lock. The artifact's entry is byte-equal before and after the move.
   - **Considered:** asking the owner again, which the acceptance's scope does not need: the
     artifact, the advisory, the repository and the last day are the same.
   - **Chosen because:** the binding exists so that the record matches no other repository's
     lock; this repository's lock after its own move is still this repository's lock. The
     owner is told on the page that reports the move.
   - **Applies to:** `.config/checks/dependency-vulnerabilities/policy.toml`.
4. **The supply image is rebuilt and bound in this Change.**
   - **Rests on:** the image's manifest, which hashes `package-lock.json`, and the projection
     check, which refuses a head whose manifest inputs differ from the bound image's commit.
   - **Considered:** rebinding after the landing, which leaves the lane's own GitLab pipeline on
     an image without npm 12.2.3 and fails the projection check.
   - **Chosen because:** the check requires it before a proof.
   - **Applies to:** `.config/ci/pipeline.cue` and the two generated pipelines.

## Risks / Trade-offs

- [npm 12.2.3 is hours old] -> ETHOS's declared release age is 0 hours. The suite, the hosted
  runs on three platforms and the full proof run with it before the head lands.
- [A later npm release before the tag blocks again] -> the same move again, or the owner's
  disposition for the three bundled findings; the release kit's audit before the tag would
  show it.
- [The reading of the release's candidate on the governed copies used the earlier npm] -> the
  reading exercises ETHOS's own commands and no npm; the session that keeps the governed
  repositories reads the final candidate again beside the executed run.
