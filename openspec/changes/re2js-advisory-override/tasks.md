# Tasks

## 1. Supply

- [x] 1.1 Override markdownlint-cli2's re2js with 2.8.8 in `package.json` and re-resolve the
  product lock with the locked npm. Done when the lock holds one production `re2js` 2.8.8 with its
  registry integrity, no other lock entry changes, and OSV reports no advisory for re2js 2.8.8.
  (The lock diff is the one `node_modules/re2js` entry; OSV-Scanner 2.7.0 reports
  GHSA-gg6h-894w-4m9c for the `dev` lock and nothing for this one, 2026-10-29.)
- [x] 1.2 Record the override under Security in `[Unreleased]`. Done when the changelog validates.
  (`changelog_errors` reports none.)

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` to GitHub and GitLab.
- The next release carries the override. The supply owner rebuilds and rebinds the Linux supply
  image from an accepted head.
