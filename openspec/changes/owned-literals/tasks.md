# Tasks

## 1. Declaration

- [x] 1.1 Declare the branch roles in a `[branch]` table, key `[binding] files` by role and add
      `binding_path(role)`. Done when the paradigm model loads both, `binding_path` returns
      `.ethos/<file>` for each role, and the readers of the whole binding set read its values.
      (The four role cases pass; `_binding_gaps` and the reference closure read the values.)
- [x] 1.2 Build `BranchRolePolicy` defaults from `[branch]`. Done when a policy built without
      arguments carries the declared names and the branch-role tests pass unchanged. (A policy
      built under a replaced `[branch]` table carries its names; the earlier cases are unchanged.)

## 2. Readers

- [x] 2.1 Build every binding carrier path, binding file name, gap code and message in `src/` from
      `binding_path`. Done when the check reports none of them in `src/`. (None remain.)
- [x] 2.2 Read `VERSION`, `CHANGELOG.md` and the multi-segment branch values from `paradigm.release`
      and `[branch]`, directly or through `BranchRolePolicy`, and give formation's initial branch
      the accepted role. Done when the check reports 0 for `src/`. (It reports 0; formation runs
      `git init -b` with the accepted name, and its 69 related cases pass.)

## 3. Check

- [x] 3.1 Add the architecture check derived from the declaration. Done when it reports 0 for
      `src/`, records the count for `tools/`, fails on a planted carrier path and a planted branch
      value, and ignores npm's `dev` dependency type. (`tools/` keeps 19; the planted cases find 1
      or 2 each, and a docstring or a single-word name finds none.)

## 4. Specification

- [x] 4.1 Write the `repository-paradigm` delta. Done when strict validation and the cumulative
      archive simulation pass. (12 of 12 specs valid after the simulated archive.)

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass;
  the archive commit changes only OpenSpec documents, which its own proof checks.
