## MODIFIED Requirements

### Requirement: Repository Hygiene Gate

ETHOS SHALL make repository-shape hygiene visible through one owner script and a
separated policy file so host-local residue, text-shape drift, merge markers,
large tracked files, malformed JSON, and forbidden stash guidance cannot hide in
Git, global ignores, provider projections, or hook-local behavior.

#### Scenario: Hidden root host-local residue fails closed

- **WHEN** `tools/ci/scripts/run-repository-hygiene.sh` runs
- **THEN** the gate reads `.config/checks/repository-hygiene/policy.toml` as the
  policy owner
- **AND** globally ignored root host-local files such as `.DS_Store`,
  `Thumbs.db`, and `Desktop.ini` fail with a required hygiene error
- **AND** the gate reports the residue without deleting, stashing, or promoting
  it into repository truth
- **AND** CI providers, pre-commit hooks, and local CI call the owner script
  instead of duplicating the policy body.
