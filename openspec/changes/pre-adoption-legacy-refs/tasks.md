# Tasks

## 1. Failing cases first

- [x] 1.1 Add the fixture of the reported shape (a legacy table naming `master`, `integration/dev`,
      `task/` and `submit/`; `master` and a `submit/` ref at commits before the adoption; no release
      binding at the accepted head) and its cases: the abandonment retires; the rename; the
      unshared `master`; the `accepted_ff` closeout after the landing; the release from `main` at
      the legacy commit; the absorbed retirement of `master` before its rename; the forge
      retirement refused as today. Done when the first six fail on the base and the seventh
      passes: 12 of the 14 drafted cases failed on `024c217bf`, the two forge cases passed
      (`7a328784c`).
- [x] 1.2 Add the shapes the review named: a legacy accepted name beside a pre-adoption release
      ref, and a profile deleted after the adoption. Done when the first renames and the second
      blocks with `repository_historical_identity_invalid:.ethos/profile.toml`.

## 2. The retirement repair

- [x] 2.1 Admit the paradigm's default policy for a claimed retirement at an accepted head with a
      valid profile and no release binding, and read the accepted head's table in the legacy role
      protection, in one commit (`9ce7b69d1`). Done when the abandonment case passes, the deletion
      stays refused where the accepted head holds no profile, and the absorbed retirement of
      `master` before its rename blocks with `legacy_role_ref_protected`.
- [x] 2.2 Ask the hook's deletion predicate in the abandonment's derivation and in its apply
      preflight (`f16c64597`). Done when a refused deletion blocks the derivation with no operation
      persisted, and a persisted operation whose deletion now refuses removes no worktree.
- [x] 2.3 Read the accepted table at the accepted ref's head, not at the asking root's HEAD. Done
      when a root checked out before the table gets `legacy_role_ref_protected` for `master`.
- [x] 2.4 Apply the model review of 2026-11-21 to the retirement repair: a release binding that
      cannot be honored keeps the refusal; each legacy table is read on its own; the accepted
      table comes from the accepted line, never from a root's own HEAD; the derivation and the
      apply ask one function. Done when the cases of the module and of the two retirement test
      modules pass, the stubs of the deletion predicate asserting the ref and head they were asked.

## 3. The rename repair

- [x] 3.1 Read a pre-adoption pre-state under the accepted head's identity, only after a
      historical read fails (`a6b336fd0`). Done when the rename, the mirror's fast-forward and the
      release cases pass, the deleted-profile shape still blocks, and the read-budget cases of
      `tests/unit/adapters/repo/test_historical_profile_identity.py` pass unchanged.
- [x] 3.2 Refuse the unshared legacy ref by name and read the accepted head in the hook's shape
      check, through one classification that 3.1 also asks (`0cd0a92d0`). Done when the unshared
      case blocks with `legacy_role_rename_history_unshared:master`, a legacy ref whose history
      carried and dropped the profile blocks with
      `repository_historical_identity_invalid:.ethos/profile.toml`, and each preview agrees with
      its apply.
- [x] 3.3 Test the identity reader itself, which every Git effect passes. Done when it returns the
      accepted identity for a pre-state the accepted head descends from and refuses an unshared
      one with `repository_historical_identity_invalid:`.
- [x] 3.4 Count no revision for a ref that an effect creates at the commit the same effect deletes
      (the owner approved the sentence on 2026-11-21), and lend the accepted identity to pre-states
      only. Done when a legacy ref at a retired-schema profile renames, a rename onto a
      pre-adoption commit resolves the accepted identity, and a move or a rewind of another ref
      onto that commit blocks with `repository_profile_invalid`.
- [x] 3.5 Classify from complete history: walk every parent of a merge, and answer `dropped` in a
      shallow repository. Done when the classification's cases pass.
- [x] 3.6 Apply the second model review (`063fc595b..a0c1cfe00`, 10 comments): one creation for
      one deletion is a rename; a recorded effect is read without today's accepted head; HEAD is
      read only where the standard accepted ref is missing, and keeps its table's protection where
      no accepted line can be named; a release binding's absence is read from the tree; only the
      one admitted classification passes. Done when the three regressions that failed on
      `a0c1cfe00` pass.

## 4. Specifications and documents

- [x] 4.1 State the deltas for what is built. Done when `openspec validate --strict` passes and
      every scenario of the deltas has a case.
- [x] 4.2 Add two Fixed entries to the Unreleased section of `CHANGELOG.md`, one for each repair
      (`9c42d4ca6`). Done when the commit's Markdown checks pass on the changelog.

## 5. Acceptance

- [x] 5.1 Run the chain in the fixture of the reported shape: retire the `submit/` ref, rename,
      land with `accepted_ff`, closeout; and a release from a pre-adoption previous head. Done when
      every step passes and `candidate/dev`, `dev` and `main` read the landed head.
- [ ] 5.2 Pass the pre-check, readiness and one full proof at the lane's head, with the model
      reviews of its product code triaged (two so far, 14 and 10 comments), and the hosted runs of
      that head on both forges. Done when each passes before the cut of 2026-11-26.
