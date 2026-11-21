# Proposal

## Why

A governed repository adopted ETHOS under a legacy branch-role table (release branch `master`,
proposal prefix `submit/`), with refs at commits made before the adoption, which hold no
repository profile. Two operations it needs fail, measured on 2026-11-20 in a fixture of its shape:

- An abandonment of its pre-adoption proposal ref previews `derived`, removes the worktree, and the
  hook then refuses the ref deletion: the repository stands in `partial_transition`. The code is
  narrower than the accepted scenario "No strict policy governs the deletion", which blocks only
  when neither the deleted commit nor the accepted head carries a release binding or a valid
  profile, and the abandonment does not ask the hook's own predicate first.
- The accepted closeout cannot rename `master` to `main`, and after a rename nothing can move
  `main`: the rename's effect, the release mirror's fast-forward and the release each read the
  legacy commit's identity, which a commit with no profile does not have. The hook's shape check
  also reads the table at the deleted ref's own commit, so a preview promises a rename that the
  apply refuses whenever a legacy ref stands before the table's commit. One shape of the same
  repository (a legacy ref with no shared history) is refused under a code that names another
  cause, `repository_profile_invalid`.

The owner moved both repairs into 0.2.0-beta.12 on 2026-11-20 (「提前」), chose the rename
by shared history (「按照你建议的方式推进」), and approved the two requirement changes
below the same evening. The census of 2026-11-20 found one of fourteen governed
repositories in this shape; the code paths are general.

## What Changes

- A deletion's policy: an accepted head with a valid profile and no release binding selects the
  paradigm's default policy, for a claimed retirement only (hand deletions stay refused). In the
  same change, the legacy role protection also reads the accepted head's committed table, as the
  accepted scenario "A protected legacy role ref" says, so a pre-adoption legacy release ref is
  protected before its rename, from every root of the repository.
- A lane abandonment asks the hook's deletion predicate before it persists an operation, and its
  apply asks again before it removes anything; a refusal comes before any worktree is removed.
- A pre-state revision in whose history no commit carries the repository profile, and from which
  the accepted branch's head descends, is read under the accepted head's identity.
- The rename refuses a legacy role ref with no profile in its history and no shared history with
  the accepted head by name, `legacy_role_rename_history_unshared:<branch>`; the hook's shape
  check reads the deleted commits and the accepted head.

Not in this Change: a legacy role ref at a commit whose profile is of a retired schema. Its
rename needs a rule for a ref that an effect creates at the commit the same effect deletes, which
changes a sentence of the identity requirement; that rule waits for the owner's answer (asked
2026-11-21) and takes a Change of its own.

Not breaking for a repository that has no legacy table. One added refusal: the protection of a
legacy release ref before its rename, which is the accepted scenario's own text (a ruled defect
fix under the law freeze). Everything else admits what is refused today.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: the one exception to "Historical effect identity survives profile
  schema evolution" is a requirement of its own, "A pre-adoption pre-state is read under the
  accepted identity", which also carries the sentence on current effects; the scenario
  "Historical identity cannot be guessed" narrows accordingly. "Absorbed-ref retirement previews
  agree with the prepared hook" gains three scenarios.
- `repository-paradigm`: "Accepted closeout renames legacy role refs" also triggers on a legacy
  release name alone; the refusal of the unshared case is a requirement of its own, "An unrelated
  legacy role ref is never renamed".

## Impact

`src/ethos/adapters/admission/ref_move_policy.py`, `adapters/admission/role_rename.py`,
`adapters/mutation/lane_retirement/abandonment.py`, `effects.py` and `operation.py` there,
`adapters/repo/git_effect_observation.py`, `adapters/repo/profile.py`,
`adapters/mutation/branch_roles.py`, `contracts/codes/gaps.toml`, their tests. The forge
retirement of published legacy refs is not changed (the owner, 2026-11-20: deleted by hand).
