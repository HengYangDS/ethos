# Tasks

## 1. Status

- [x] 1.1 Name the current Work Lane's Lease in the inline status summary. Done when tests show
      `lease_generation`, `lease_expires_at` and `lease_seconds_left` in `summary` for a Work Lane,
      also when the payload budget moves `data` into an artifact, and none of them for the accepted
      root. The tests fail first. The status tests failed first: `lease_summary` did not exist. Now
      a Work Lane summary names generation, expiry and 3,600 seconds left, another role and a
      missing Lease name nothing, and the summary stays inline when the payload budget moves 40 KB
      of detail to an artifact.
- [x] 1.2 Point status at the renewal near expiry. Done when a test shows the renewal preview with
      less than two hours left, the resumption preview once the Lease has expired, and neither with
      two hours or more. The renewal preview is next at 3,600 and 7,199 seconds, none at 7,200, and
      the resumption preview at 0 and -5.

## 2. Renewal

- [x] 2.1 Preview renew and resume from the current Lease. Done when tests show that a preview
      without coordinates plans the exact operation and names the apply command with all four
      coordinates, and that `--apply` without them refuses with `lease_coordinates_required`. The
      tests fail first. The CLI tests failed first. Now a preview without coordinates plans on the
      current Lease and names the exact apply command for renew and resume, and `--apply` without
      them refuses with `lease_coordinates_required` before any effect. 947 tests of the lease,
      lane, domain, handoff, result and status suites pass.

## 3. Specification and notes

- [x] 3.1 Add the `command-plane` requirement. Done when strict validation and the cumulative
      archive simulation pass. Strict validation and the archive simulation pass: 2 requirements
      added, 12 of 12 specifications valid.
- [x] 3.2 Describe both in the command reference and name them in the Unreleased notes. Done when
      `changelog_errors` reports nothing. The operational roots reference describes both, and
      `changelog_errors` reports nothing.
