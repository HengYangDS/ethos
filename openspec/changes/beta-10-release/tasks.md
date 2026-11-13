# Tasks

## 1. Release entry

- [ ] 1.1 Move the product version to 0.2.0-beta.10. Done when the lane's `ethos --version` reports
      0.2.0-beta.10 and the tests that read the version or the changelog pass.
- [ ] 1.2 Turn `[Unreleased]` into the `0.2.0-beta.10` entry, completed from the landed Changes and
      the release build's audit. Done when `changelog_errors` reports nothing with 0.2.0-beta.10 as
      its release target and the entry names every advisory that the audit reports.

## 2. Acceptance

- [ ] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
