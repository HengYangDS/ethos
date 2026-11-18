# Tasks

## 1. Supply

- [x] 1.1 Pin npm 12.2.3 and lock it natively. Done when the lock moves npm and seven of its
      bundled packages alone, holds 555 entries, and every `resolved` entry is the public
      registry.
      (At `47f141353`: nine entries differ from the lock before, the root entry, npm and seven
      bundled packages; 555 entries before and after; 407 entries resolve from the public registry
      and 147 are bundled.)
- [x] 1.2 Name the lock's digest in the disposition for picomatch 2.3.2. Done when the test that
      holds the record's digest against the committed lock passes, and the audit at the lane
      head passes with one approval and reports the three bundled findings as unfixed upstream.
      (At `6b71a52fc` the record's digest equals the committed lock's, and the module that holds it
      passes, 54 cases. The audit with these locks decides `pass`: one approval, no unapproved
      subject, four subjects unfixed upstream, the three that npm bundles and picomatch 4.0.7. Task
      1.9 then accepts the three.)
- [x] 1.3 Rebuild the CI supply image from this lane's proposal ref and bind it. Done when the
      bound digest and its source commit are in `.config/ci/pipeline.cue` and the CI projection
      check passes.
      (`d15ca07a7` bound the image of `47f141353`; readiness passed there, 28 of 28. Tasks 1.8 and
      1.10 replace that binding.)
- [x] 1.4 Record the move in the entry of 0.2.0-beta.11 and name npm 12.2.3 in its known open
      defects. Done when the changelog check reports nothing with 0.2.0-beta.11 as its release
      target.
      (`changelog_errors` with the target 0.2.0-beta.11 reports nothing at `6b71a52fc` and at the
      lane head.)
- [x] 1.5 Move the `minimatch` override to 11.0.9 and lock it. Done when the lock moves the
      override and the two packages that follow it, holds 555 entries, and `npm ls` is clean.
      (At `af29ab68b`: `minimatch` 11.0.9, `dompurify` 3.4.18 and `ignore` 7.0.16 below `globby`
      differ from the lock of `47f141353`; 555 entries; `npm ls --all` exits 0.)
- [x] 1.6 Move the Python lock and the floors of the moved direct requirements. Done when
      `uv lock --check` passes for the root and the fixture project, an upgrade dry run reports
      no change at the lock step of 2026-11-18T03:27:00Z, and the dependency declaration check
      reports no gap.
      (17 packages moved at `af29ab68b`; both checks pass; the dry runs of 03:27Z reported no change
      for the root and the fixture project; the declaration check is one of the 28 readiness gates
      that pass. Task 1.10 returns one of the 17, uv.)
- [x] 1.7 Move uv, Syft and Grype in the Mise declaration and its lock, and Mise's floor and
      bootstrap to 2026.11.9. Done when the six digests equal the release's `SHASUMS256.txt`,
      the lock's other entries are unchanged, and the test that names the locked Syft passes.
      (The lock's eight other tools are equal entry by entry before and after, and its format
      revision is 3. `af29ab68b` bound the two Windows digests of the release's archives, and five
      hosted Windows jobs refused them; `d20cc1c2a` binds the executables, each found by the file
      that the digest of 2026.11.8 named in that release's sums. The test passes, 7 cases. Task 1.10
      returns uv's entry.)
- [x] 1.8 Move the supply image's base to the uv 0.13.9 image by digest, then rebuild and bind
      the image again. Done when the bound digest names the commit that holds every moved lock
      and the CI projection check passes.
      (`af29ab68b` moved the base and `6b71a52fc` bound the image built from `d20cc1c2a`; readiness
      passed there, 28 of 28. Task 1.10 returns the base to the uv 0.13.8 image and binds again.)
- [x] 1.9 Add the dispositions for the three findings that npm 12.2.3 bundles. Done when the
      audit at the lane head passes with four approvals, the product's decision on the saved
      evidence passes with a newer npm as the registry's latest, and the test that holds the
      records' digest against the committed lock passes.
      (In a clone of `6b71a52fc` with the records: the audit decides `pass` with four approvals and
      reports picomatch 4.0.7 alone; `evaluate_dependency_acceptance` on the saved evidence with a
      newer npm as the latest passes with the records, blocks on exactly the three subjects without
      them, and blocks from 2026-12-03; the module passes, 54 cases. `2e0ddedfc` and `d5ed8df93`
      correct the records' stated grounds: glob and minimatch have fixed releases that no npm
      bundles. No test holds the records' node and integrity fields yet; that test is the first item
      of the next lane.)
- [x] 1.10 Return uv to 0.13.8 in the Python lock, the Mise declaration and the supply image's
      base, with a resolver hold, then rebuild and bind the image. Done when the uv entry of
      each lock equals the one of `7913f66bc`, the hosted Windows job passes the release
      inventory, and the CI projection check passes.
      (At `612e5e04e` the uv entry of the Mise lock and the image's base line equal those of
      `7913f66bc`, and the Python lock differs from that of `af29ab68b` in uv alone. `43194202c`
      binds the image built from `612e5e04e`; readiness passes there, 28 of 28. GitHub's
      qualification run 44242416428 of `43194202c` passes the release inventory on Windows x64 and
      on Windows arm64.)

## 2. Acceptance

- [x] 2.1 Pass the model review of this Change's range, the precheck and readiness at the lane
      head, and read the hosted runs of that head on both forges. Done when each passes on the
      committed head.
      (The model reviews of `7913f66bc..43194202c` are five records, each triaged: 0, 2, 3, 2 and 2
      comments. The static precheck and readiness pass at `43194202c`, 28 of 28. GitHub's push run
      44242391349 and qualification run 44242416428 of `43194202c` pass; the qualification's Windows
      suite leg, an observation, fails on the same four tests as at `7913f66bc`. GitLab's pipeline
      16356 of `43194202c` passes.)

## Workflow follow-up

- The full proof of the archived head, then the copies run on its candidate, as the follow-ups
  of `beta-11-head-move` state them.
- The supply owner prunes the superseded image digests from the Linux CI guest, by the owner's
  authorization of 2026-11-10.
- The draft `audit-latest-named` gains this case: a new release of a bundling package that
  leaves its bundled findings as they were.
- A row of the next release adapts the configuration reader to the OpenSpec CLI 2.1 and moves
  the pin; until then the measure of supply currency reports the pin as held.
- uv is held below 0.13.9 by a resolver constraint that nothing reads: the next supply move scans
  the Windows executable of the newest uv and lifts the hold by hand when it carries the data.
- A draft names that nothing compares a bound bootstrap digest with the release's sums before a
  hosted job downloads the executable.
