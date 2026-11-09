## ADDED Requirements

### Requirement: A verified retained original is not an authored document

An original that the docs registry verifies against the declared retained origins is not an
authored document: the front-matter, decision-record-name, authored-name and formatter rules
SHALL NOT apply to it, and the repair SHALL plan no edit of it. An original whose observation has a
gap, differs from its declaration or is missing SHALL keep every one of those rules.

#### Scenario: A verified original

- **WHEN** the native observer verifies a declared original's bytes and mode
- **THEN** the paradigm reports no front-matter, decision-record, authored-name or formatter gap
  for it, and `ethos lane repair-paradigm` plans no edit of it

#### Scenario: An original that does not verify

- **WHEN** a declared original's bytes or mode changed, the taxonomy is malformed, or the original
  is declared without an observation
- **THEN** the paradigm judges it as an authored document

#### Scenario: An authored document

- **WHEN** a tracked document under the docs root is no declared original and has no front matter
- **THEN** the paradigm reports its front-matter gap
