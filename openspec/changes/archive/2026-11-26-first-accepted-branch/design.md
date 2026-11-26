# Design

## Context

The reference-transaction hook decides a prepared ref move in this order
(`_prepared_reference_report`): a recorded signature repair or role rename; the policy that
governs the move, resolved from the committed tree of the old value or, for a zero old value, of
the new one; then, for the accepted branch, the candidate runner. With no candidate checkout at
the new value the runner's report is `candidate_semantic_runner_unavailable`.

A repository without an accepted branch has no candidate branch, so the creation of the accepted
branch can never reach a runner. `ethos lane candidate`, which creates the candidate branch, needs
the accepted branch. The product holds no other route.

Git reports a prepared creation as a move from a zero old value. It reports a forced move of an
existing branch (`git branch -f`, `git switch -C`, `git update-ref` without an old value) with the
same zero old value (Git 2.56.1, run on 2026-11-24).

## Goals / Non-Goals

**Goals:**

- A repository whose only root is its release branch reaches the state of one that created its
  accepted branch before arming, by a plain Git command.
- Nothing that the hook admits today is refused, and nothing else that it refuses is admitted.
- `ethos status` names the step.

**Non-Goals:**

- A product command that creates the branch, a record of the creation, or a proof of the created
  head.
- A clone whose remote already shows the accepted branch, and a local accepted branch that is
  behind its peer. Both stay as they are and are listed as known defects.
- A command in the hook's refusal of a creation.
- A branch copy (`git branch -c`, `-C`), which Git writes without a reference transaction and
  which therefore meets no hook, for any protected branch. Measured on accepted `dev`; listed as
  a known defect.
- A change that Git's own status hides (assume-unchanged, skip-worktree): hidden from every
  reader of status in the product.

## Decisions

1. **One function states the shape, and it takes no selector.**
   `first_accepted_branch(repo, policy, ref_name, old_value, head)` in `ref_move_policy.py`
   answers whether a move is the admitted creation. The hook asks it for a protected move before
   the candidate runner. No parameter, flag, environment value or operation name selects it.
   - **Considered:** a new operation name `accepted.bootstrap` in `ref_transition_operation`, as
     the first prototype had.
   - **Chosen because:** the name reached every reader of an operation and decided nothing; and
     the prototype derived it from the zero old value, which a forced move shares.
2. **Only a move from a zero old value is asked, and the branch's absence is read from the ref
   store.**
   - **Rests on:** the Git run above, and a control: the first prototype, asked through the armed
     hook, moved an existing accepted branch by each of the three forced commands.
   - **Applies to:** a closeout's advance carries its old value and is never asked, so the hook
     reads nothing more for it than on accepted `dev`. For a zero old value the ref store decides
     with `git show-ref --verify` of the full name.
3. **The asking checkout is clean at the release head.**
   The new value, the release branch's head and the checkout's `HEAD` are one commit, and
   `git status --porcelain --untracked-files=all` is empty. A linked detached checkout at that
   commit may ask. The hook's Git reads no user-level or system-level configuration, as every Git
   call of the product, so only the repository's own ignore rules apply.
   - **Chosen because:** `ethos lane candidate` asks for a clean accepted root next, by the same
     reading.
4. **No candidate branch exists.** With one, the repository is past its bootstrap, and the move
   belongs to the candidate runner.
5. **Every remote has exactly Git's default fetch refspec and no tracking ref of the branch.**
   The configured value of `remote.<name>.fetch` is compared with
   `+refs/heads/*:refs/remotes/<name>/*`, and `refs/remotes/<name>/<accepted>` must not exist.
   A remote list that Git cannot read refuses.
   - **Rests on:** three reads of the text against the code. A reader of refspec forms was built
     and withdrawn: each round found a form that it admitted or skipped wrongly (a destination
     without its full name, an empty value, a one-sided wildcard that makes `git remote` fail and
     emptied the list).
   - **Considered:** interpreting every refspec form; asking only the tracking ref.
   - **Chosen because:** the condition is a protection, and one exact string cannot be misread. A
     repository with another fetch layout keeps today's refusal, which is narrower than the ask
     of 2026-11-24 said and loses nothing that passes today.
   - **Limit:** the hook reads local refs and configuration only. A clone that has not fetched
     since the peer gained the branch is admitted. Its local branch then cannot follow the
     peer's, as a branch created by hand before arming cannot today.
6. **The transaction must be the asking checkout's own.**
   Git names another repository to its hook in `GIT_DIR` (`git --git-dir=<other> update-ref …`
   run inside this checkout), and every read of the product is of the working directory's
   repository. `_own_repository` in the hook compares the two common directories, for this
   admission only. A caller's `GIT_COMMON_DIR` makes Git write the ref and run the hooks of that
   common directory while `GIT_DIR` stays the checkout's own, and the product's Git reads run
   without it, so the comparison would answer for the wrong repository: the admission refuses
   whenever `GIT_COMMON_DIR` is set. Git sets none for a checkout of its own, linked or not.
   The model review of the first patch found this; both cases are driven through the armed
   hook.
   - **Chosen because:** without it a checkout that lacks the branch would admit a forced move of
     another repository's existing branch. The general confusion, for every other decision of
     the hook, is older than this Change and is not touched: closing it there refuses moves that
     pass today.
7. **`ethos status` asks the same function with the hook's policy resolution.**
   `first_accepted_branch_step(repo, head)` resolves the policy with `resolve_ref_move_policy`
   for the creation, as the hook does, and returns the instruction or nothing. `_candidate_step`
   in `inspection.py` returns it on a clean checkout of the release branch that reports a missing
   candidate, and the candidate bootstrap on an accepted root as before. A pending role
   rebinding is still named first.
   - **Chosen because:** a step that `status` names and the hook refuses is the defect of this
     Change over again.
   - The step is an instruction, not a command: it is a Git command, and the next-step contract
     classifies only `ethos` commands.
8. **The created head is an adopted baseline.**
   The creation requires no proof and writes no record. Run in the armed fixture: the candidate
   bootstrap and a lane's start pass on it; a first landing is refused with `proof_not_proven`
   and passes with a proof; the closeout advances the branch; a push of the baseline before that
   closeout is refused. Each step answers as for a branch created by hand before arming.
9. **The created head carries a readable policy source.**
   Its committed tree holds a release binding that parses, or no release binding and a valid
   repository profile: `_strict_ref_policy` or `_unbound_policy` of the head returns a policy.
   - **Rests on:** the fourth reading of the text against the code, its eighth finding: for a
     zero old value, a release binding that is present and does not parse is read as absent, and
     the paradigm's default policy is then selected where the committed profile is valid. The
     same reading holds on accepted `dev` for every move from a zero old value.
   - **Chosen because:** the accepted text rejects missing or mismatched committed policy inputs,
     and `_unbound_policy` already refuses that state on the retirement path; a condition that
     cannot be read does not hold.

## Risks / Trade-offs

- [The hook reads topology itself for this one move] → it reads four refs, the checkout's status
  and the remotes' refspecs, all local, and holds no state. The accepted text scopes "hooks
  consume closeout's prepared decision" to candidate promotion.
- [A bare Git command creates the accepted branch with no record] → the same state exists today
  for every repository that created the branch before arming; the first landing meets the proof
  floor.
- [A stale clone creates a branch that cannot follow its peer] → `status` says to fetch first;
  after a fetch the mapped ref exists and the creation is refused. The state itself is today's.

## Migration Plan

None for repositories that have an accepted branch. A repository in the circle upgrades its
runtime, runs `ethos status` on its release root and follows the step.
