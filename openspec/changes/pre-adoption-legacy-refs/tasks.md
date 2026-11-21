# Tasks

## 1. Failing cases first

- [ ] 1.1 Add the fixture of the reported shape (a legacy table naming `master`, `integration/dev`,
      `task/` and `submit/`; `master` and a `submit/` ref at commits before the adoption; no release
      binding at the accepted head) and its cases: the partial abandonment retires; the rename; the
      unshared `master`; the `accepted_ff` closeout after the landing; the release from `main` at
      the legacy commit; the absorbed retirement of `master` before its rename; the forge
      retirement refused as today. Done when the first six fail on the accepted head and the
      seventh passes. Drafted 2026-11-21 as `tests/unit/lanes/test_pre_adoption_legacy_refs.py`, 14
      cases: 12 fail on the head `024c217bf` and pass with the sketches; 2 (forge retirement) pass
      on both. Shapes kept: the half-done state (a lock file on the ref stops the deletion after
      the worktree is removed), a retired-schema profile (fails without rule b1), a legacy accepted
      name beside a pre-adoption release ref, and a lane whose HEAD table names `master`.
- [ ] 1.2 Add the shapes the review named: a legacy accepted name as well as a legacy release name
      only; a profile deleted after the adoption; a legacy ref at an old-schema profile. Done when
      each fails or passes as the design says, on the accepted head.

## 2. The retirement repair

- [ ] 2.1 Admit the paradigm's default policy for a claimed retirement at an accepted head with a
      valid profile and no release binding, and read the accepted root's table in the legacy role
      protection, in one commit. Done when the abandonment case passes and the absorbed retirement
      of `master` before its rename blocks with `legacy_role_ref_protected`.
- [ ] 2.2 Ask the hook's deletion predicate in the abandonment's derivation. Done when a refused
      deletion blocks before any worktree is removed and no operation is persisted.

## 3. The rename repair

- [ ] 3.1 Read a pre-adoption pre-state under the accepted head's identity, and count no revision
      for a ref created at the commit the same effect deletes (this second part, rule b1, and its
      sentence of the identity requirement WAIT for the owner's answer, asked 2026-11-21; without
      it the retired-schema case stays out of the module). Done when the rename, the mirror's
      fast-forward and the release cases pass, and the deleted-profile shape still blocks.
- [ ] 3.2 Refuse the unshared legacy ref by name and read the accepted root's head in the hook's
      shape check, asking 3.1's own "predates the adoption" predicate (one function, two callers).
      Done when the unshared case blocks with `legacy_role_rename_history_unshared:master`, a legacy
      ref whose history carried and dropped the profile blocks with
      `repository_historical_identity_invalid:.ethos/profile.toml`, each preview agrees with its
      apply, and no case ends in an uncaught error.
- [ ] 3.3 Add one test for each effect kind that passes the pre-state identity reader. Done when
      each kind's test passes with the exception and its refusal of an unshared revision holds.

## 4. Specifications and documents

- [ ] 4.1 Apply the deltas. Done when `openspec validate` passes and every scenario named in the
      deltas exists once.
- [ ] 4.2 Add one Fixed entry to the Unreleased section of `CHANGELOG.md` naming both repairs and
      the added protection. Done when the changelog check passes.

## 5. Acceptance

- [ ] 5.1 Run the chain end to end in the fixture of the reported shape on the built code: retire
      the `submit/` ref, rename, land with `accepted_ff`, closeout, release. Done when every step
      passes and the refs read `candidate/dev`, `dev` and `main` at the landed head.
- [ ] 5.2 Pass the pre-check, readiness and one full proof at the lane head, and the hosted runs of
      that head on both forges. Done when each passes before the cut of 2026-11-26.
