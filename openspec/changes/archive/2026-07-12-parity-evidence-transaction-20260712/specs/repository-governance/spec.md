## MODIFIED Requirements

### Requirement: Parity evidence is committed before Work Lane proof

ETHOS SHALL treat stale configured generic parity evidence as an explicit
evidence-freshness proof gap. A Work Lane that changes the parity-relevant tree
shall refresh and commit its parity evidence before it executes proof or lands.

#### Scenario: parity-relevant Work Lane source makes generic evidence stale

- **GIVEN** a Work Lane has committed a parity-relevant source or contract change
- **AND** its tracked generic parity evidence no longer matches the resulting
  parity-relevant semantic tree
- **WHEN** `ethos quality evidence-freshness --json` or executed proof evaluates
  the Work Lane
- **THEN** ETHOS reports the parity evidence invalidity as a required gap
- **AND** it returns the Work-Lane-owned parity refresh package
- **AND** it does not require a candidate or accepted root to write tracked evidence.

#### Scenario: evidence recording commit precedes proof and land

- **GIVEN** an admitted Work Lane refreshes generic parity evidence after its
  source commit
- **WHEN** it commits only the resulting evidence record and then executes proof
- **THEN** semantic-tree freshness accepts the evidence-recording commit
- **AND** the Work Lane may proceed to normal candidate landing
- **AND** candidate and accepted roots remain protected from direct parity writes.
