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
- Every locked supply of this repository at its newest stable release at the lock step, by the
  owner's direction of 2026-11-18, except what a recorded reason holds.

Non-Goals:

- The rule's gap: a finding behind the latest release blocks although the latest release holds
  it too. It is the subject of the draft `audit-latest-named`, which gains this case.
- The OpenSpec CLI 2.1, whose adoption needs product code (decision 6).
- `complexipy` 9, Python 3.15 and any prerelease channel, as the move of 2026-11-14 held them.
- The supply of the governed repositories, which each moves in a lane of its own.

## Decisions

1. **npm moves first and alone; the rest of the supply follows in the same Change.**
   - **Rests on:** the audit's own record of the stopped proof, whose three unapproved subjects
     all lie in `node_modules/npm/node_modules/`, and the registry's publication time of npm
     12.2.3; then the owner's direction of 01:06 UTC for the whole supply, and the measure of
     01:11 UTC that names what is behind.
   - **Considered:** npm alone, which was this decision before the direction and leaves a
     release head that is known to be behind on its first day; a second Change after the
     landing, which runs the proof, the hosted runs and the copies run of the governed
     repositories a second time for the same supply; three dispositions without a move, which
     accept a risk where an upgrade exists.
   - **Chosen because:** the head's proof, its hosted runs and the copies run execute once
     either way, and they are the acceptance of a supply move. The npm move stays its own commit
     (`47f141353`) with its own bound image, so the head before the rest is a head that passed
     readiness and its hosted run, and the lane can return to it by reverting later commits.
   - **Applies to:** every file that the proposal's impact names.
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
5. **One lock step, recorded, and nothing after it.**
   - **Rests on:** the move of 2026-11-14, whose first decision this repeats, and this morning's
     measure: a release of `filelock` appeared inside the lock step itself.
   - **Considered:** following every later release until the tag, which moves the head again and
     runs its acceptance again each time.
   - **Chosen because:** a release head needs one supply that its whole acceptance tested. The
     lock step's time is in the tasks; a release after it belongs to the next move.
   - **Applies to:** `uv.lock`, `package-lock.json` and `.config/mise/mise.lock`.
6. **The OpenSpec CLI stays at 2.0.0.**
   - **Rests on:** the configuration reader's JavaScript test with 2.1.0 installed in a scratch
     clone: `openspec_config_invalid:TypeError`, because 2.1.0 no longer exports
     `readKeptSharedSkills` from `core/shared-skill-target.js`. With 2.0.0 in the same clone the
     test passes.
   - **Considered:** adapting the reader here, which is product code in the reader that every
     status and every write admission call, three days before a tag.
   - **Chosen because:** a supply move changes pins and locks. The adaptation is a row of the
     next release, and it also decides whether the reader keeps importing the CLI's internals.
   - **Applies to:** `package.json`; the hold is named in the proposal and the entry.
7. **The Mise lock keeps its format revision, and only the moved tools' entries change.**
   - **Rests on:** the lock before and after `mise lock` for the three tools: three version
     lines differ and no other entry; the six bootstrap digests are the ones that the release's
     `SHASUMS256.txt` publishes.
   - **Considered:** `mise lock --upgrade` to the newer format, which rewrites every entry.
   - **Chosen because:** the smaller change, as on 2026-11-14.
   - **Applies to:** `.config/mise/mise.lock` and `.config/checks/ci-projection/policy.toml`.
8. **The locked Syft's rule for Node is read again.**
   - **Rests on:** Syft's classifier source at the tags `v1.57.1` and `v1.57.2`: the rule
     `nodejs-binary` matches a file named `node` alone in both, so the release inventory still
     declares the Node of a Windows runtime itself. Read, not run on a Windows runtime.
   - **Considered:** removing the declaration path, which the test asks for once Syft classifies
     `node.exe`; it does not yet.
   - **Chosen because:** the test that names the locked Syft exists to force this reading.
   - **Applies to:** `tests/unit/ci/delivery/test_release_node_declaration.py`.
9. **The three findings that npm bundles are accepted until 2026-12-02 for this repository's lock.**
   - **Rests on:** the owner's answer of 2026-11-18 04:31 UTC to the page that reported this
     move (accept until 2026-12-02, for this repository's own lock alone), and a re-evaluation
     of the saved audit evidence by the product's own decision with a newer npm as the
     registry's latest: without the records it blocks on exactly these three subjects, with
     them it passes, and after their last day it blocks again.
   - **Considered:** no acceptance, which lets every npm release before the tag stop the proof,
     the hosted qualification or the release's own audit, each time at the price of a new head
     and its whole acceptance; an acceptance without the lock's digest, which the product's
     policy would carry to every governed repository.
   - **Chosen because:** the upgrade is taken already and repairs no advisory, so the acceptance
     only keeps today's verdict when a newer npm appears. Each record names the bundling npm's
     integrity, as the policy asks for a bundled node, and this lock's digest, so it stops
     matching when the locked npm or the lock changes.
   - **Applies to:** `.config/checks/dependency-vulnerabilities/policy.toml`; the entry's known
     open defects state the acceptance and its last day.

## Risks / Trade-offs

- [npm 12.2.3 and the other moved releases are hours or days old] -> ETHOS's declared release
  age is 0 hours. The suite, the hosted runs on three platforms and the full proof run with
  them before the head lands.
- [A moved tool changes a verdict: ty 0.0.105, Grype 0.122.0, 17 Python packages] -> in a
  scratch clone the type check, the audit, the dependency declarations, the JavaScript, Markdown,
  prose and configuration sessions and seven test modules passed before the lane received the
  move; the proof and the hosted runs are the acceptance. A regression is fixed or held in this
  Change with its reason.
- [`min_version` 2026.11.9 refuses a host whose Mise is older] -> this host's Mise is 2026.11.9;
  CI jobs install the bound executable by digest.
- [A later npm release before the tag blocks again] -> the three records of decision 9 hold
  until 2026-12-02. After that day, or once the lock changes, the audit reads the findings
  again, and a supply move or a new acceptance decides.
- [The reading of the release's candidate on the governed copies used the earlier npm] -> the
  reading exercises ETHOS's own commands and no npm; the session that keeps the governed
  repositories reads the final candidate again beside the executed run.
