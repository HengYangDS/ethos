# Proposal

## Why

Two defects in the release path surfaced after `0.2.0-alpha.20`.

- **Every release turns GitLab red.** GitLab's Linux jobs check the locked supply image's input
  hashes before anything else, and `package-lock.json` is one of those inputs. The root npm
  workspace makes npm record the launcher's version in that lock, and the launcher's version
  projects the product version. The `0.2.0-alpha.20` bump (`959166ef4`) changed that lock, and
  GitLab pipeline 13407 then refused `dev` at `e5e49a105` with `package-lock.json: FAILED`. A
  second landing must bind a new image after every release, as `ci-supply-alpha-19` did after a
  dependency change.
- **A created repository cannot make its first release.** `ethos adopt --create` forms `dev` and
  `candidate/dev` but no `main`. Closeout under an `accepted_ff` mirror requires `main` to exist,
  and `ethos land --release` requires it to equal the accepted head. No transition creates it, and
  the reference-transaction hook rightly refuses a raw `git branch main`. ddwg-film is blocked at
  `37549a9`, and filmkit will be. Closeout also misreports the absent branch as
  `release_mirror_diverged`: it reads `main` with `git rev-parse` without `--verify`, which prints
  the literal name for an absent ref.

A release also edits 16 lines in 3 test modules, because the version tests name the current version
literally.

## What Changes

- **The launcher leaves the root workspace.** `package.json` no longer declares `distributions/npm`
  as a workspace, and native npm regenerates `package-lock.json` without the launcher's entries.
  `npm run ethos` and the launcher's package test already address it by path.
- **One version projection.** The version check keeps `distributions/npm/package.json` as the only
  projection and refuses a lock that records the product version.
- **Tests read the version owner.** The version tests compare with `VERSION` and its PEP 440 form,
  so a release edits no test. The release guide no longer moves a lock entry.
- **Closeout creates an absent release mirror.** Under `accepted_ff`, closeout creates a missing
  `main` at the candidate head in its one ref transaction, under that transaction's exact ref
  intent, also when `dev` already equals the candidate. A present `main` that is not an ancestor
  still blocks as diverged.
- **The release branch is read by its full ref** through `--verify`, so an absent branch is never
  mistaken for a commit.
- **CHANGELOG.** Entries under `[Unreleased]`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `distribution`: the launcher is a standalone package; no dependency lock records the product
  version, so a version bump changes no supply-image input.
- `repository-governance`: accepted closeout creates an absent `accepted_ff` release branch.

## Impact

- **Files.** `package.json`, `package-lock.json`, `src/ethos/repository/release/identity.py`,
  `src/ethos/adapters/mutation/accepted/promotion.py`,
  `src/ethos/adapters/repo/git_ref_worktrees.py`, the release guide, and the version, promotion
  and closeout tests. Product Python does not grow.
- **Supply.** This Change edits `package-lock.json` itself, so the image is rebuilt from `dev` once
  after it lands and bound in the `0.2.0-alpha.21` release Change. Later releases leave the image
  valid.
- **Existing checkouts.** A checkout whose `node_modules` predates the new lock fails the Node
  supply check with `node_package_supply_lock_mismatch`; prewrite then reports
  `openspec_official_cli_missing`. `mise run bootstrap`, or the npm seed it runs, repairs it, as for
  any lock change. The accepted root and every lane that refreshes onto this head need it once.
- **Governed repositories.** A repository formed by `ethos adopt --create` that declares
  `accepted_ff` gains `main` at its next closeout after it binds `0.2.0-alpha.21`. Under an
  independent mirror, a first release still needs an existing `main`.
