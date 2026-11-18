# Tasks

## 1. Supply

- [ ] 1.1 Pin npm 12.2.3 and lock it natively. Done when the lock moves npm and seven of its
      bundled packages alone, holds 555 entries, and every `resolved` entry is the public
      registry.
- [ ] 1.2 Name the lock's digest in the disposition for picomatch 2.3.2. Done when the test that
      holds the record's digest against the committed lock passes, and the audit at the lane
      head passes with one approval and reports the three bundled findings as unfixed upstream.
- [ ] 1.3 Rebuild the CI supply image from this lane's proposal ref and bind it. Done when the
      bound digest and its source commit are in `.config/ci/pipeline.cue` and the CI projection
      check passes.
- [ ] 1.4 Record the move in the entry of 0.2.0-beta.11 and name npm 12.2.3 in its known open
      defects. Done when the changelog check reports nothing with 0.2.0-beta.11 as its release
      target.
- [ ] 1.5 Move the `minimatch` override to 11.0.9 and lock it. Done when the lock moves the
      override and the two packages that follow it, holds 555 entries, and `npm ls` is clean.
- [ ] 1.6 Move the Python lock and the floors of the moved direct requirements. Done when
      `uv lock --check` passes for the root and the fixture project, an upgrade dry run reports
      no change at the lock step of 2026-11-18T03:27:00Z, and the dependency declaration check
      reports no gap.
- [ ] 1.7 Move uv, Syft and Grype in the Mise declaration and its lock, and Mise's floor and
      bootstrap to 2026.11.9. Done when the six digests equal the release's `SHASUMS256.txt`,
      the lock's other entries are unchanged, and the test that names the locked Syft passes.
- [ ] 1.8 Move the supply image's base to the uv 0.13.9 image by digest, then rebuild and bind
      the image again. Done when the bound digest names the commit that holds every moved lock
      and the CI projection check passes.
- [ ] 1.9 Add the dispositions for the three findings that npm 12.2.3 bundles. Done when the
      audit at the lane head passes with four approvals, the product's decision on the saved
      evidence passes with a newer npm as the registry's latest, and the test that holds the
      records' digest against the committed lock passes.
- [ ] 1.10 Return uv to 0.13.8 in the Python lock, the Mise declaration and the supply image's
      base, with a resolver hold, then rebuild and bind the image. Done when the uv entry of
      each lock equals the one of `7913f66bc`, the hosted Windows job passes the release
      inventory, and the CI projection check passes.

## 2. Acceptance

- [ ] 2.1 Pass the model review of this Change's range, the precheck and readiness at the lane
      head, and read the hosted runs of that head on both forges. Done when each passes on the
      committed head.

## Workflow follow-up

- The full proof of the archived head, then the copies run on its candidate, as the follow-ups
  of `beta-11-head-move` state them.
- The supply owner prunes the superseded image digests from the Linux CI guest, by the owner's
  authorization of 2026-11-10.
- The draft `audit-latest-named` gains this case: a new release of a bundling package that
  leaves its bundled findings as they were.
- A row of the next release adapts the configuration reader to the OpenSpec CLI 2.1 and moves
  the pin; until then the measure of supply currency reports the pin as held.
