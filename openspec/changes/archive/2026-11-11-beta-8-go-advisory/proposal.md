# Proposal

## Why

Go published GO-2026-6859 (CVE-2026-97054) on 2026-11-11: an HTTP/1 server in `net/http` can crash.
The Go tools that ETHOS bundles, `cue`, `vale` and `shfmt`, are built with Go versions before the
fix, and no upstream release of them is built with a fixed Go yet. The 0.2.0-beta.8 entry names
its known open defects, so it names this one too. The tag also follows tonight's proof window and
hosted CI, which end after midnight, so the entry's date moves to the day of the tag.

## What Changes

- The 0.2.0-beta.8 entry lists GO-2026-6859 among its known open defects, with the bundled tools it
  affects, how ETHOS runs them and when a fix will reach ETHOS.
- The entry's date is 2026-11-12, the day the tag is created.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A release entry changes no requirement, so `skip_specs: true` applies.

## Impact

`CHANGELOG.md`.
