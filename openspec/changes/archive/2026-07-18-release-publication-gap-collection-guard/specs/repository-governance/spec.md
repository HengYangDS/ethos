## ADDED Requirements

### Requirement: Release policy accepts declared topology gap collections

The release-policy reducer SHALL propagate publication-topology diagnostics only
when the topology read model declares `required_gaps` as a list. A malformed
non-list value SHALL NOT become character-wise release-policy gaps.

#### Scenario: Malformed topology gaps do not invent failures

- **WHEN** `publication_topology.required_gaps` is not a list
- **THEN** `release_policy_report` does not append synthetic gaps from that
  value

#### Scenario: Declared topology gap list remains visible

- **WHEN** `publication_topology.required_gaps` is a list
- **THEN** `release_policy_report` includes each declared gap
