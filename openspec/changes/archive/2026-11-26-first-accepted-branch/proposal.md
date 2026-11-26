# Proposal

## Why

A repository that is adopted while its release branch is its only branch, and whose hooks are then
armed, cannot get an accepted branch. Three routes meet, and each waits for another:

- `git switch -c dev main` and `git branch dev main` are refused by the reference-transaction hook
  with `candidate_semantic_runner_unavailable`: the hook sends every move of the accepted branch's
  name to the candidate runner, and a repository without a candidate branch has none.
- `ethos lane candidate` blocks with `candidate_bootstrap_requires_clean_accepted_root`: it needs
  the accepted branch.
- `ethos status` blocks with `candidate_branch_missing` and names no next step.

One governed repository stands in this state. It can start no lane and land nothing, and its
signature repair cannot be previewed, because that needs the accepted branch as well.

A repository that created its accepted branch by hand BEFORE arming its hooks is in none of this:
`ethos status` names the candidate bootstrap, the bootstrap passes, and lanes start. Measured in
the product's own armed fixture on 2026-11-24, a branch created through the hook by the shape of
this Change and a branch created by hand before arming answer alike at every later step: the
candidate bootstrap, a lane's start, a first landing that is refused without a proof and passes
with one, its closeout, and a push.

## What Changes

- The reference-transaction hook admits the creation of an absent accepted branch at the release
  branch's head, from a clean checkout at that commit of the same repository, when no candidate
  branch exists, the created head carries a release binding that parses or a valid profile, and
  every configured remote has Git's default fetch refspec and no tracking ref of the branch.
  Every other move of the accepted branch is judged as before.
- The absence is read from the ref store. Git reports a forced move of an existing branch with
  the same zero old value as a creation, so the old value alone decides nothing.
- `ethos status` on such a checkout names the creation as its next step, preceded by a fetch
  where a remote is configured.
- The created head is an adopted baseline: it carries no proof and no closeout record. It is the
  state that a branch created by hand before arming has today.
- Requirement texts: five new requirements in `repository-governance` and one in `adapters`,
  and three changed accepted requirements. The new ones hold one rule, split so that each
  requirement body stays within OpenSpec's 500 characters.

Not breaking: the hook admits one move that it refuses today and refuses nothing that it admits
today.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: five requirements added, two modified.
- `adapters`: one requirement added, one modified in its body and in one scenario.

## Impact

- Code: `src/ethos/adapters/admission/ref_move_policy.py` (the shape and the status step),
  `src/ethos/adapters/repo/hook/admission.py` (one question before the candidate runner, and the
  check that the transaction is the checkout's own), `src/ethos/application/inspection.py` (the
  step toward a candidate branch as one function) and `system/surfaces.toml` (`GIT_DIR` and
  `GIT_COMMON_DIR`, which the hook reads).
- Not repaired, and listed as known defects: a clone whose remote already shows the accepted
  branch still cannot create it locally under armed hooks; a local accepted branch that is behind
  its peer cannot follow it and no result says so; a creation that the hook refuses gets no
  command from the hook; a branch copy moves a protected branch without any hook.
- Rollback: before the next tag, a Change that removes the question and restores the texts.
  After a release it is shipped behaviour, and a created accepted branch stays.
