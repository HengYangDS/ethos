## ADDED Requirements

### Requirement: An absent accepted branch is created at the release head

The armed reference-transaction hook SHALL admit a creation of the accepted branch that no recorded
effect has prepared when, as the transaction is prepared, the accepted branch does not resolve in
the repository's ref store, the new value is the release branch's head, no candidate branch exists,
and the conditions of the requirements "The creation of an absent accepted branch reads its
checkout" and "The creation of an absent accepted branch reads the remotes" hold.

#### Scenario: A checkout at the release head creates the accepted branch

- **GIVEN** a governed repository with armed hooks, no `dev`, no candidate branch and no remote,
  with `main` checked out and clean
- **WHEN** `git switch -c dev main` or `git branch dev main` runs
- **THEN** the hook admits the creation and `dev` is at the release head

#### Scenario: A creation at another commit, or beside a candidate branch, is not admitted

- **GIVEN** a governed repository with armed hooks, no `dev` and no candidate checkout
- **WHEN** `git branch dev <commit>` or `git switch -c dev <commit>` names a commit other than the
  release head, or runs while a candidate branch exists
- **THEN** this requirement does not admit the creation
- **AND** the hook rejects it, and no accepted branch is created

### Requirement: The creation of an absent accepted branch reads its checkout

The admission of the requirement "An absent accepted branch is created at the release head" SHALL
also require that a Git command in a checkout of the repository, with no `GIT_COMMON_DIR` set,
prepares the transaction in that same repository, that this checkout is at the new head and Git's
status reports no staged, unstaged or untracked change there, and that the created head's committed
tree carries a release binding that parses, or none and a valid repository profile.

#### Scenario: A creation from a checkout elsewhere or with a change is not admitted

- **GIVEN** a governed repository with armed hooks, no `dev` and no candidate checkout
- **WHEN** `git branch dev main` runs in a checkout that is at another commit or has a staged,
  unstaged or untracked change
- **THEN** the creation is not admitted
- **AND** the hook rejects it, and no accepted branch is created

#### Scenario: A creation with `GIT_COMMON_DIR` set is not admitted

- **GIVEN** a governed repository with armed hooks, no `dev`, no candidate checkout and no remote,
  with `main` checked out and clean
- **WHEN** `git branch dev main` runs with `GIT_COMMON_DIR` set in its environment
- **THEN** the creation is not admitted
- **AND** the hook rejects it, and no accepted branch is created

### Requirement: The creation of an absent accepted branch reads the remotes

The admission of the requirement "An absent accepted branch is created at the release head" SHALL
also require that each remote that the repository's own configuration declares has exactly Git's
default fetch refspec, `+refs/heads/*:refs/remotes/<remote>/*`, and no tracking ref of the accepted
branch. A condition of that admission that the hook cannot read does not hold.

#### Scenario: A remote that has shown the branch, or does not fetch every branch, does not admit

- **GIVEN** a governed repository with armed hooks, no `dev` and no candidate checkout
- **WHEN** `git branch dev main` runs while a remote's tracking ref of `dev` exists, or a remote's
  fetch refspecs are not exactly the default one, as in a clone of one branch
- **THEN** the creation is not admitted
- **AND** the hook rejects it

### Requirement: An admitted creation of the accepted branch is an adopted baseline

A creation that the requirement "An absent accepted branch is created at the release head" admits
is not an accepted advance, and the created head SHALL be an adopted baseline: the creation
requires no proof and writes no record, and a landing onto that head requires its proof as every
landing does. A move of an accepted branch that
exists is not a creation, whatever old value the transaction reports. That requirement admits no
other move of the accepted branch and refuses none.

#### Scenario: A forced move is not a creation

- **GIVEN** the accepted branch exists and no candidate checkout does
- **WHEN** `git branch -f`, `git switch -C` or `git update-ref` without an old value moves it to
  the release head
- **THEN** the hook rejects the move and the branch keeps its head

### Requirement: Status names the creation of an absent accepted branch

On a clean checkout of the release branch where the conditions of the requirement "An absent
accepted branch is created at the release head" hold, `ethos status` SHALL name the creation as
its next step, preceded by a fetch where a remote is configured; a pending role rebinding
is named before it.

#### Scenario: Status names the creation

- **GIVEN** a clean checkout of `main` where the conditions hold, and no pending role rebinding
- **WHEN** `ethos status` runs there
- **THEN** its next step is the instruction that creates the accepted branch at the release head
- **AND** with a configured remote the instruction begins with a fetch of every remote

## MODIFIED Requirements

### Requirement: Protected-ref semantics are candidate-commit bound

Protected-ref transitions SHALL run admission from the Git-common selected
immutable runtime in isolated mode and SHALL read candidate policy from the
candidate HEAD's committed tree, or, for a creation admitted as an adopted
baseline, from the created head's committed tree. They SHALL reject
ignored candidate runtimes, accepted-checkout interpreters, inherited
`PYTHONPATH`, and missing or mismatched committed policy inputs. The proof floor
SHALL match the committed repository role.

#### Scenario: Candidate runtime state attempts to override committed semantics

- **WHEN** a candidate ignored interpreter, inherited `PYTHONPATH`, accepted
  interpreter, or uncommitted policy file differs from the candidate HEAD
- **THEN** the protected-ref transition does not execute or read that state
- **AND** missing or mismatched committed candidate inputs block the transition.

#### Scenario: A product-root control revision carries adopter proof

- **WHEN** the committed candidate tree is a product root but its proof was
  generated while an adopter profile still classified the worktree
- **THEN** admission requires the product proof floor and reports every missing
  product gate
- **AND** it does not reinterpret the proof through a `full` option or weaken
  the promotion floor.

### Requirement: Native accepted-ref admission agrees with transition proof

The accepted-ref hook SHALL use the repository-transition proof selector used by
promotion preflight. Complete same-HEAD executions with the same accepted
intent, current policy, verifier and claim MAY differ in their execution facts,
plan and effect without blocking that transition. Candidate ancestry, exact
prepared ref intent and Git CAS remain independent requirements of an accepted
advance. Ordinary full-binding proof queries SHALL retain their stricter
conflict behavior.

#### Scenario: Two valid executions precede one accepted transition

- **GIVEN** two current proofs share the accepted assertion and policy but have
  different execution facts, plans and effects
- **WHEN** the authorized accepted-ref update reaches the native Git hook
- **THEN** the hook admits the same proof set as promotion preflight
- **AND THEN** the exact ref update succeeds only with its prepared intent.

#### Scenario: Different assertions remain contradictory

- **WHEN** the same HEAD carries proofs with different verifier or claim
- **THEN** accepted-ref admission blocks their contradiction
- **AND THEN** an ordinary full-binding query also remains strict.
