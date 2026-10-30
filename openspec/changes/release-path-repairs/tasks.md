# Tasks

## 1. Version Outside the Locks

- [x] 1.1 Remove the `distributions/npm` workspace from `package.json` and regenerate
      `package-lock.json` with native npm, then run the npm seed. Done when the lock's diff removes
      exactly `packages[""].workspaces`, `packages["distributions/npm"]` and the
      `node_modules/@agentic-workflow/ethos` link, and `npm run ethos -- --version` and the npm
      package test pass.
      (At `61c84f7c8` npm's `--package-lock-only` diff removes those three entries and nothing
      else, 18 lines; the seed installs 408 packages without the link; the launcher reports its
      version, and the package test passes 4/4.)
- [x] 1.2 Keep `distributions/npm/package.json` as the one version projection, and refuse a lock
      that records the product version at its root, its root package or a `distributions/npm`
      entry. Done when the version tests cover the refusal.
      (`test_projected_package_versions_refuse_parallel_owners` and
      `test_version_file_is_the_single_product_owner_and_manifests_are_projections` at
      `61c84f7c8`.)
- [x] 1.3 Make the version tests read `VERSION`, and stop the release guide moving a lock entry.
      Done when no test names the current product version.
      (At `61c84f7c8` no test, tool or product module names `0.2.0-alpha.20` or `0.2.0a20`, and
      the version, policy and identity tests pass, the release build included.)

## 2. Release Mirror Birth

- [x] 2.1 Read the release branch with `ref_head` in `promotion.py`, plan an absent `accepted_ff`
      release branch as a creation at the candidate head, check ancestry only for a present branch,
      and let `worktree_sync_gap` pass when it selects no worktree, whatever its diff. Done when a
      real-Git closeout without `main` leaves `dev` and `main` at the candidate head, both when
      `dev` advances and when it already equals the candidate, and the diverged case still blocks.
      (`test_accepted_ff_closeout_creates_an_absent_release_branch` failed on both cases with
      `accepted_transition_invalid` before the repair and passes at `61c84f7c8`, with
      `test_candidate_promotion_creates_an_absent_release_mirror` and
      `test_candidate_promotion_rejects_a_diverged_release_mirror_before_effect`. Before the
      refresh the closeout, worktree, identity and release test modules passed 121 tests; at
      `61c84f7c8` the version, boundary, supply, promotion and new closeout tests passed 109.
      `source-budget` passes with 69,989 product lines.)

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
