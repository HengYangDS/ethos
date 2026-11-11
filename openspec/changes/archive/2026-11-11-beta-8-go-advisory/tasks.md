# Tasks

## 1. Name the advisory and the release date

- [x] 1.1 Add GO-2026-6859 to the 0.2.0-beta.8 entry's known open defects and date the entry
      2026-11-12. Done when `changelog_errors` reports nothing with 0.2.0-beta.8 as its target and
      Prettier accepts the file. In `7a5d408ca`: the entry names GO-2026-6859 with the three tools,
      their Go versions and how ETHOS runs them, and is dated 2026-11-12; `changelog_errors` reports
      nothing with 0.2.0-beta.8 as the target, and Prettier and Vale accept the file.

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. At `7a5d408ca` the static precheck passed and readiness passed 28 of 28 gates.
