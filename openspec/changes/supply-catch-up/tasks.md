# Tasks

## 1. Supply

- [ ] 1.1 Move the Mise floor and the CI bootstrap version to 2026.10.25 with the six official
      executable digests from the release's `SHASUMS256.txt`. Done when `ci_templates` and the
      projection tests pass and the lane's Mise reports no missing tool.
- [ ] 1.2 Move the Python lock with `uv lock --upgrade` and the direct floors with it. Done when
      `uv lock --check` passes, the `dependencies` gate reports no gap and the release audit decides
      `pass`.
- [ ] 1.3 Bind a supply image built from the moved inputs. Done when the hosted `supply_image`
      workflow built and pushed it from this lane, `lane project --check` reports the projections
      conforming and every GitLab supply job selects its digest.
- [ ] 1.4 Name the moves in the Unreleased notes. Done when the changelog validates.

## Workflow follow-up

- Archive this Change, prove the archived head once, then land after `v0.2.0-alpha.28` is tagged,
  close out, bootstrap and publish `dev` and `main` to GitHub and GitLab.
