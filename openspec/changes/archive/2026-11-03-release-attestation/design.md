# Design

## Context

See [proposal.md](proposal.md). The `release-platforms` legs build and qualify each platform's
wheel and runtime archive. The `release-publish` job downloads their artifacts, and
`tools/ci/delivery/release_assets.py` checks every archive and wheel against its qualification
evidence and copies it under its published name, which keeps its bytes and digest. The job then
runs `gh release create` over `build/release/out/assets/*` with `contents: write` as its only
permission.

## Goals / Non-Goals

**Goals:**

- Every archive and wheel of a release carries a GitHub artifact attestation of the run that
  published it, made before the release exists.

**Non-Goals:**

- Moving adopters' pins to the GitHub backend, retiring the `http:` declaration asset, or changing
  runtime selection; `github-pin` owns those.
- Attesting `SHA256SUMS`, the Mise declaration or the notes, which are derived from the attested
  files.
- Verifying attestations inside ETHOS.

## Decisions

- **Attest in the publication job.** It holds every file under its final name after the
  assembler's checks, so one step covers all platforms; renaming leaves digests unchanged, so the
  attestation also covers each leg's uploaded bytes.
- **Attest before `gh release create`.** A failed attestation then stops the publication instead
  of leaving a release without provenance.
- **The action pinned by commit**, like every action in the model: `actions/attest-build-provenance`
  v4.2.2, `4d101475d8b20a2381f78447822ac1eab6504dd8`, its latest release.

## Risks / Trade-offs

- [The attestation service fails during a release] → The job fails before the release is created,
  and the release run is rerun; no unattested release appears.
- [The projection test cannot run the release job] → The step's effect is confirmed on the next
  release with `gh attestation verify`, which the workflow follow-up records.
