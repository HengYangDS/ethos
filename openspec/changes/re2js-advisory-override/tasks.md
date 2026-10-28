# Tasks

## 1. Supply

- [ ] 1.1 Override markdownlint-cli2's re2js with 2.8.8 in `package.json` and re-resolve the
  product lock with the locked npm. Done when the lock holds one production `re2js` 2.8.8 with its
  registry integrity, no other lock entry changes, and OSV reports no advisory for re2js 2.8.8.
- [ ] 1.2 Record the override under Security in `[Unreleased]`. Done when the changelog validates.

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` to GitHub and GitLab.
- The next release carries the override. The supply owner rebuilds and rebinds the Linux supply
  image from an accepted head.
