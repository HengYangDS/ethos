# Tasks

## 1. Security policy

- [x] 1.1 Add the root `SECURITY.md` and the Unreleased Added line. Done when prewrite admits both
      paths, Prettier and Vale accept both files, and the paradigm reports no root gap at the lane
      head. Evidence: d4c67f19f adds `SECURITY.md` and the Added line; prewrite admitted both paths
      (17:39:07 to 17:39:12); Prettier and Vale accepted both files and the Change's documents; the
      packaged paradigm reports no gap for `SECURITY.md` and a `root-catalog` gap for an unadmitted
      `SECRETS.md`.

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: the precheck passed against 5eb47348b with 0 findings (17:52:28 to 17:52:35),
      and readiness passed 28 gates at 5eb47348b with the 6 heavy gates left to the proof (17:52:35
      to 17:54:36).
