# Design

## Context

**Supply.** GitLab's Linux jobs run in a locked supply image and check its `input.sha256` against
the checkout before they provision anything. The manifest hashes the CI projection policy, the
Mise configuration and lock, the image's Dockerfile and ignore file, `uv.lock`,
`package-lock.json` and the quality sample's `uv.lock`. Its contract test states the intent: a
product-code edit must not invalidate unchanged locked tool bytes.

The product version still reaches one of those inputs. The root `package.json` declares
`distributions/npm` as a workspace, and npm records each workspace's version in `package-lock.json`
(`packages["distributions/npm"].version`), beside a `node_modules/@agentic-workflow/ethos` link. The
launcher's version projects `VERSION`, and `projected_package_versions` deliberately requires the
lock to repeat it. Every release therefore changes the lock. The image is built only by the
`supply_image` dispatch on `dev`, so a second landing must bind the new digest, and GitLab refuses
checkouts between the two. `uv.lock` has no such entry, because the project's version is dynamic.
No other image input names the version.

The version tests also name the current version: 16 lines in `test_version_command.py`,
`test_policy_attestation.py` and `test_version_identity.py` change at every release, and the release
guide tells a release to move the lock entry.

**Release branch.** The paradigm fixes the role names: release `main`, accepted `dev`, candidate
`candidate/dev`. `ethos adopt --create` forms the accepted and candidate refs only. Under
`[release] mirror = "accepted_ff"`, `_promotion_effect` in `promotion.py` requires the release
branch to exist before closeout, and `ethos land --release` requires it to equal the accepted
head. Nothing creates it, and the hook refuses a raw move of a protected mirror. The check itself
runs `git rev-parse main` without `--verify`. For an absent ref git prints `main` and exits 128, so
closeout reports `release_mirror_diverged`. Its unit test mocks git with empty output and never saw
this.

Two more steps would refuse a zero object ID: the closeout preflight's `worktree_sync_gap` diffs
`previous..head` before it looks at any worktree, and `is_ancestor` fails for a zero ID. Ref
admission already admits a creation: `accepted_advance_gaps` skips the fast-forward check for a
zero ID, the effect observes an absent ref as zero, and Git passes a zero old value to the hook.

## Goals / Non-Goals

**Goals:**

- No dependency lock records the product version, so a version bump changes no supply-image input.
- A release changes only `VERSION`, the launcher's projection and the release entry.
- The version tests keep their meaning: the console, the release policy and the build identity
  report what the version owner holds.
- A created repository that declares `accepted_ff` gains `main` at its first closeout, through the
  existing transaction and admission.

**Non-Goals:**

- Publishing the launcher to a registry, or changing how it finds a checkout.
- Changing the image's inputs, its build or the GitLab bootstrap.
- Rebinding the image in this Change. That needs a build from `dev` after landing.
- A first release under an independent mirror. `accepted/release.py` still requires an existing
  `main` there, a known gap with no governed repository that needs it yet.
- Creating `main` at `adopt --create`. A repository may never release, and its mirror is declared
  later in `.ethos/release.toml`.

## Decisions

- **The launcher is a standalone package, not a workspace.** The workspace is the only path by
  which the version enters the lock. Nothing consumes the link: `npm run ethos` runs
  `distributions/npm/bin/ethos.mjs` by path, the package test packs that directory, the launcher
  finds a checkout by its files, and the Node supply skips link entries. Native npm
  (`npm install --package-lock-only --ignore-scripts`) regenerates the lock; no tool rewrites it.
  - *Rejected:* hashing the lock without the workspace entry. The image hashes whole native files,
    and a filtered digest would need a second normalizer for one key.
  - *Rejected:* rebuilding and rebinding the image after each release. That is the current
    behaviour, and it leaves GitLab refusing checkouts between two landings.
  - *Rejected:* stamping the launcher's version at pack time. npm requires the field in
    `package.json`, and a release-time writer would become a second version owner.
- **The version check keeps one projection and owns the refusal.** `projected_package_versions`
  compares `distributions/npm/package.json` with `VERSION`, as before. A lock that records the
  version, at its root, its root package or a `distributions/npm` entry, is a parallel owner and is
  refused with `package_version_parallel_owner:package-lock.json`. Re-adding the workspace therefore
  fails where the version is owned, not later at a GitLab checkout. A substring check over the
  image inputs was rejected: the lock legitimately holds other packages at versions such as `0.2.0`.
- **Tests read the version owner.** The version tests read `VERSION` through `product_version` and
  compare with it and with its PEP 440 form, `Version(product)`. The assertion that only restated
  the literal goes, because the owner test already checks that the manifests project it.
- **An absent mirror is born at closeout.** `_promotion_effect` and `current_acceptance` read
  `refs/heads/<release>` with `ref_head`, which verifies the ref. An absent branch reads as the zero
  object ID at the candidate head's width, and the release update expects it, so the closeout's one
  atomic transaction creates `main` at the candidate head. When `dev` already equals the candidate,
  that transaction creates `main` alone and asserts `dev`. Ancestry is checked only for a present
  branch. `worktree_sync_gap` ignores an unreadable diff when it selects no worktree, as for a zero
  `previous`; with a worktree selected, the unreadable diff still blocks.
  - *Rejected:* a separate command that creates the release branch. It would be a second writer of
    a protected mirror, outside the transaction that keeps both refs equal.
- **Tests.** The promotion matrix mocks `ref_head` instead of `run_git`, replaces the
  missing-branch refusal with the creation it now plans, and keeps the diverged refusal. A real-Git
  closeout covers a repository without `main`, both when `dev` advances and when it already equals
  the candidate.

## Risks / Trade-offs

- **Stale `node_modules` in existing checkouts.** Each `node_modules/.package-lock.json` still lists
  the link, so the Node supply check fails with `node_package_supply_lock_mismatch` and prewrite
  reports `openspec_official_cli_missing`, as after any lock change. → The lane runs the npm seed
  right after regenerating the lock. The accepted root bootstraps after landing, and the landing
  notice asks every lane holder to bootstrap after refreshing.
- **A deleted `main` is recreated** by the next closeout of an `accepted_ff` repository. → It is
  recreated at the accepted head that it mirrors, which loses no content. Publication still refuses
  a peer whose `main` is not a fast-forward.

## Migration Plan

- Land, then publish `dev` and `main` to both peers. GitLab keeps refusing checkouts until the image
  is rebound, as it has since `0.2.0-alpha.20`.
- Dispatch the `supply_image` build on `dev` at the landed head, and bind its digest in the
  `0.2.0-alpha.21` release Change. That release's version bump then leaves the image valid.
- ddwg-film and filmkit bind `0.2.0-alpha.21`. Their next closeout creates `main`, and
  `ethos land --release --expect-head <head> --release-head <head> --tag <tag>` tags it.
- **Rollback.** Revert this Change. The workspace returns, the next image build hashes the old lock
  again, and closeout again requires an existing `main`.

## Open Questions

- None.
