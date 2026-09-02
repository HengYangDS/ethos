## ADDED Requirements

### Requirement: Semantic Reference Closure Distinguishes Use From Assertion

ETHOS SHALL classify a retired path as a current consumer only when a current
carrier uses that path as an executable, import, configuration, declaration, or
navigable reference. A normative statement, test assertion, or explanatory
mention that requires or reports the path's absence SHALL NOT itself constitute
consumption.

#### Scenario: Canonical specification requires absence

- **WHEN** an official canonical OpenSpec requirement names a retired path only
  to require that the path be absent
- **THEN** repository semantic closure SHALL NOT report that specification as a
  consumer of the retired path
- **AND** the independent absence check SHALL remain enforceable.

#### Scenario: Canonical specification links to a retired path

- **WHEN** an official canonical OpenSpec specification contains a navigable
  link whose resolved destination is a retired path
- **THEN** repository semantic closure SHALL report the specification as a
  current consumer of that retired path.

#### Scenario: Executable consumer remains

- **WHEN** current source, configuration, import syntax, command syntax, or a
  declared runtime owner resolves a retired path
- **THEN** repository semantic closure SHALL report the exact consumer
- **AND** prose polarity SHALL NOT suppress that executable relation.
