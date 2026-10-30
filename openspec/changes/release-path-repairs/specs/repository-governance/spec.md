## ADDED Requirements

### Requirement: Accepted closeout creates an absent release mirror

When `.ethos/release.toml` declares `[release] mirror = "accepted_ff"` and the release branch does
not exist, accepted closeout SHALL create it at the candidate head in its one ref transaction,
under that transaction's exact ref intent, also when the accepted branch already equals the
candidate head. A present release branch that is not an ancestor of the candidate head SHALL still
block closeout.

#### Scenario: A created repository closes out under a declared mirror

- **WHEN** a repository formed by `ethos adopt --create` declares `accepted_ff` and has no `main`
- **THEN** closeout leaves `dev` and `main` at the proven candidate head
- **AND** `ethos land --release` can then select that head

#### Scenario: The release branch has diverged

- **WHEN** `main` exists and is not an ancestor of the candidate head
- **THEN** closeout blocks with `accepted_transition_invalid` and reports `release_mirror_diverged`
- **AND** neither protected ref moves
