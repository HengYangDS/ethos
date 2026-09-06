## ADDED Requirements

### Requirement: Commit policy applies to exact introduced commit ranges

ETHOS SHALL compile the optional tracked `.ethos/workspace.toml
[commit_policy]` declaration through the existing repository-policy owner and
apply that compiled policy only to the commits newly introduced by one proposed
Git ref update. The range projection SHALL be provider-neutral, SHALL preserve
the repository object format, and SHALL NOT reinterpret or revalidate commits
already reachable from the trusted baseline.

#### Scenario: Existing ref receives a normal fast-forward

- **WHEN** a non-delete update supplies readable remote and proposed commit
  objects
- **THEN** ETHOS validates each commit reachable from the proposed commit but
  not from the remote commit in deterministic oldest-first order
- **AND** commits already reachable from the remote commit are not revalidated.

#### Scenario: Existing ref receives a non-fast-forward update

- **WHEN** the proposed commit does not descend from the readable remote commit
- **THEN** ETHOS still reports and validates exactly the commits newly reachable
  from the proposed commit
- **AND** the existing topology and ref-movement policy independently decides
  whether the non-fast-forward effect is admissible.

#### Scenario: A new proposal ref has a trusted accepted baseline

- **WHEN** the remote object ID is the repository-native zero object ID and the
  target has proposal role
- **THEN** ETHOS resolves the declared remote's accepted ref as the trusted
  baseline and validates only the proposed commits not reachable from it
- **AND** it blocks if that baseline is absent, unreadable, or not an ancestor of
  the proposed commit.

#### Scenario: A new non-proposal ref has no trustworthy baseline

- **WHEN** the remote object ID is zero and no exact trusted baseline is supplied
  or derivable for the target
- **THEN** ETHOS fails closed with a baseline gap
- **AND** it does not substitute the root commit or scan all repository history.

#### Scenario: A delete update is observed

- **WHEN** the proposed object ID is the repository-native zero object ID
- **THEN** commit-range admission reports a no-range delete result
- **AND** it leaves deletion authority to the existing ref policy.

#### Scenario: An annotated tag is proposed

- **WHEN** either endpoint names an annotated tag object
- **THEN** range admission peels that endpoint to its exact commit before
  deriving introduced commits
- **AND** tag-object trust remains governed by the existing publication owner.

#### Scenario: Commit policy is absent or malformed at the proposed tip

- **WHEN** the proposed committed tree contains no `[commit_policy]` table
- **THEN** ETHOS adds no subject or signature constraint to the introduced range
- **AND** when the table is present but malformed, admission fails closed before
  returning a passing range result.

### Requirement: Commit signature declaration and signer trust remain distinct

For commit-range admission, `signing_required` and `signing_format` SHALL govern
the presence and format of the signature embedded in each introduced commit.
Signer authorization and trust-anchor verification SHALL remain a separate
operation-specific observation and SHALL NOT require a repository-tracked key
list or provider-specific policy parser.

#### Scenario: A declared signature is missing or has the wrong format

- **WHEN** an introduced commit lacks a required signature or carries a format
  different from the compiled policy
- **THEN** the shared range validator reports the exact commit and signature gap
- **AND** local push admission and hosted CI reach the same verdict.

#### Scenario: A lifecycle operation creates or replays commits

- **WHEN** ETHOS itself creates or replays an object under a signing requirement
- **THEN** it uses the same subject and signature-format validator
- **AND** its existing local trust verifier additionally proves the configured
  signer before any ref, Lease, or worktree effect is retained.
