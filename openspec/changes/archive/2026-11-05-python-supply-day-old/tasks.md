# Tasks

## 1. Supply

- [x] 1.1 Move the Python lock to releases at least 24 hours old. Done when `uv lock` records the
      eight moves, the lock keeps no cutoff, and the dependency audit passes. The lock records the
      eight moves with no cutoff, and the dependency hygiene and audit gates pass after the two
      direct floors rise.
- [x] 1.2 Bind a supply image built from the moved lock. Done when the hosted `supply_image`
      workflow built it from this lane and every GitLab supply job selects its digest. Run
      41994964152 built `ethos-ci-supply@sha256:6afacee6…` from `f25d3aa69`, and all five GitLab
      supply references select it.
- [x] 1.3 Name the move in the Unreleased notes. Done when `changelog_errors` reports nothing. It
      reports nothing.
