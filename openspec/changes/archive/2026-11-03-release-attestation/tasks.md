# Tasks

## 1. Release Provenance

- [x] 1.1 Add the attestation step and its two permissions to the CI model's release publication
      job, and regenerate the GitHub projection. Done when `lane project --check` reports the
      projections conforming and the projected job attests the archives and wheels before it
      creates the release. (`lane project --apply` regenerated `.github/workflows/ci.yml`: the
      job attests `ethos-*.tar.gz` and `ethos-*.whl` before "Publish the signed pre-release" and
      holds the `id-token` and `attestations` write permissions; `lane project --check` reported
      the projections conforming.)
- [x] 1.2 Cover the projected step's subjects, order and permissions in the release publication
      test, and state the release provenance in `docs/governance/provenance-and-attestation.md`
      and `CHANGELOG.md`. Done when the test passes and fails once the step is removed. (The new
      case passed with the other 8 cases of `test_release_publication.py` in 2 seconds and
      failed on a projection without the step.)

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` and `main` to GitHub and GitLab, and confirm both peers' hosted runs pass.
- After the next release, confirm that `gh attestation verify` accepts each published archive and
  wheel, and record the result with that release's evidence.
