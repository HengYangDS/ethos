# Tasks

## 1. Journey

- [x] 1.1 Take the upgrade predecessor from the latest earlier published release. Done when tests
      show three things: an unpublished entry is skipped and named; a forge error other than a
      missing release refuses instead of skipping; no published predecessor refuses with
      `release_journey_previous_missing`. The tests failed first; three mutation checks fail them.
- [x] 1.2 Record the skipped versions in the journey receipt. Done when a test reads
      `skipped_unpublished` from the receipt of a qualified tag. It reads `["v0.2.0-alpha.28"]`.

## 2. Specification and notes

- [x] 2.1 Modify the `distribution` requirement on the previous release. Done when strict validation
      and the cumulative archive simulation pass. Both pass, with all 12 specifications valid.
- [x] 2.2 Name the fix in the Unreleased notes. Done when `changelog_errors` reports nothing. It
      reports nothing, and every released entry is unchanged.
