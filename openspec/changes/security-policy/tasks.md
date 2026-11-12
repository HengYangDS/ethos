# Tasks

## 1. Security policy

- [x] 1.1 Add the root `SECURITY.md` and the Unreleased Added line. Done when prewrite admits both
      paths, Prettier and Vale accept both files, and the paradigm reports no root gap at the lane
      head. Evidence: d4c67f19f adds `SECURITY.md` and the Added line; prewrite admitted both paths
      (17:39:07 to 17:39:12); Prettier and Vale accepted both files and the Change's documents; the
      packaged paradigm reports no gap for `SECURITY.md` and a `root-catalog` gap for an unadmitted
      `SECRETS.md`.

## 2. Acceptance

- [ ] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
