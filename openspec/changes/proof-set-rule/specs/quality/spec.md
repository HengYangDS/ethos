## ADDED Requirements

### Requirement: A narrower default proof holds only offline source checks

When a gate registry's `default` proof set differs from its `full` set, every gate in the
dependency closure of `default` SHALL be offline and SHALL NOT be a package gate. A registry that
breaks this SHALL fail to load. A registry whose `default` equals `full` declares no narrower proof
and SHALL NOT be refused by this rule.

#### Scenario: A networked gate reaches a narrower default

- **WHEN** `default` differs from `full` and one gate in its dependency closure declares
  `network_policy = "required"`
- **THEN** loading the registry refuses with `default proof gate is not an offline source check`

#### Scenario: A package gate reaches a narrower default

- **WHEN** `default` differs from `full` and one gate in its dependency closure has kind `package`
- **THEN** loading the registry refuses with the same message

#### Scenario: The default proof is the full proof

- **WHEN** `default` equals `full` and holds a networked gate
- **THEN** the registry loads
