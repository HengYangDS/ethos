# Tasks

## 1. Supply

- [ ] 1.1 Pin npm 12.2.3 and lock it natively. Done when the lock moves npm and seven of its
      bundled packages alone, holds 555 entries, and every `resolved` entry is the public
      registry.
- [ ] 1.2 Name the new lock's digest in the disposition for picomatch 2.3.2. Done when the test
      that holds the record's digest against the committed lock passes, and the audit at the
      lane head passes with one approval and reports the three bundled findings as unfixed
      upstream.
- [ ] 1.3 Rebuild the CI supply image from this lane's proposal ref and bind it. Done when the
      bound digest and its source commit are in `.config/ci/pipeline.cue` and the CI projection
      check passes.
- [ ] 1.4 Record the move in the entry of 0.2.0-beta.11 and name npm 12.2.3 in its known open
      defects. Done when the changelog check reports nothing with 0.2.0-beta.11 as its release
      target.

## 2. Acceptance

- [ ] 2.1 Pass the model review of this Change's range, the precheck and readiness at the lane
      head, and read the hosted runs of that head on both forges. Done when each passes on the
      committed head.

## Workflow follow-up

- The full proof of the archived head, then the copies run on its candidate, as the follow-ups
  of `beta-11-head-move` state them.
- The supply owner prunes the superseded image digest from the Linux CI guest, by the owner's
  authorization of 2026-11-10.
- The draft `audit-latest-named` gains this case: a new release of a bundling package that
  leaves its bundled findings as they were.
