# Tasks

## 1. Supply Refresh

- [x] 1.1 Publish the supply for the accepted checkout. Done when the hosted offline smoke passes
  and the published digest is read back (run `40859418479`, source `80cce9529`, digest
  `e542b22f02b40110496b55ee0435539e9427d32a0167763503279d613993dde3`).
- [x] 1.2 Bind the published digest through the CUE owner and regenerate projections. Done when
  `lane project --check` passes and every GitLab supply job selects that digest.
  (`lane project --check`: conforming; the five GitLab supply jobs select `e542b22f…` and none the
  previous digest.)
- [x] 1.3 Validate the authored intent and CI carriers. Done when OpenSpec, the source format, the
  CI projection and the configuration quality gates pass.
  (At `647d6a96` the `openspec`, `source-format`, `ci-projection`, `config-quality`, `markdown-lint`,
  `schemas` and `prose` gates passed.)

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` and `main` to GitHub and GitLab.
- Read the GitLab pipeline of the landed head; the commit-policy job passes the supply manifest
  check.
