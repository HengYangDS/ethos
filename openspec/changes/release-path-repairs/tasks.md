# Tasks

## 1. Version Outside the Locks

- [ ] 1.1 Remove the `distributions/npm` workspace from `package.json` and regenerate
      `package-lock.json` with native npm, then run the npm seed. Done when the lock's diff removes
      exactly `packages[""].workspaces`, `packages["distributions/npm"]` and the
      `node_modules/@agentic-workflow/ethos` link, and `npm run ethos -- --version` and the npm
      package test pass.
- [ ] 1.2 Keep `distributions/npm/package.json` as the one version projection, and refuse a lock
      that records the product version at its root, its root package or a `distributions/npm`
      entry. Done when the version tests cover the refusal.
- [ ] 1.3 Make the version tests read `VERSION`, and stop the release guide moving a lock entry.
      Done when no test names the current product version.

## 2. Release Mirror Birth

- [ ] 2.1 Read the release branch with `ref_head` in `promotion.py`, plan an absent `accepted_ff`
      release branch as a creation at the candidate head, check ancestry only for a present branch,
      and let `worktree_sync_gap` pass when it selects no worktree, whatever its diff. Done when a
      real-Git closeout without `main` leaves `dev` and `main` at the candidate head, both when
      `dev` advances and when it already equals the candidate, and the diverged case still blocks.

## 3. Contract Texts

- [ ] 3.1 Modify `distribution`'s launcher, boundary and version requirements, and add
      `repository-governance`'s release mirror requirement. Done when strict validation passes and
      the simulated archive leaves every spec valid.
- [ ] 3.2 Record both repairs under `[Unreleased]` in `CHANGELOG.md`. Done when `markdown-lint` and
      `prose` pass.

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out and publish `dev` and
  `main` to GitHub and GitLab. Ask every ETHOS lane holder to bootstrap after refreshing.
- Dispatch the `supply_image` build on `dev` at the landed head, and bind its digest in the
  `0.2.0-alpha.21` release Change.
- After alpha.21, ddwg-film's closeout creates its `main`, which accepts the mirror birth for its
  consumer.
