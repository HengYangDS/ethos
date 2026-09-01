## MODIFIED Requirements

### Requirement: Product Design Contract

ETHOS SHALL keep exactly two canonical design authorities: the product design
contract SHALL own product meaning and terminal invariants, and the terminal
governance product design SHALL own the current dependency order, acceptance
boundaries, re-planning triggers, and terminal exit condition. Official OpenSpec
Changes SHALL own bounded intent and task progress; archived Changes SHALL remain
history and SHALL NOT own the current implementation queue.

#### Scenario: Design contract is audited

- **WHEN** repository architecture proof inspects current governance design
- **THEN** the product design contract and terminal governance product design
  are present
- **AND** the product contract contains the accepted semantic, lifecycle,
  projection, recovery, operational-resource, documentation, and evidence-plane
  invariants
- **AND** the terminal plan contains the complete current convergence order and
  the acceptance boundary for each bounded successor Change
- **AND** adopter observations are treated as bounded comparison evidence, not
  as a design authority or a source to copy or mutate
- **AND** neither document delegates current truth to an archived task list,
  conversation history, feedback registry, or parallel roadmap

#### Scenario: Design state is distinguished from implementation state

- **WHEN** a terminal invariant is documented before its executable owner has
  passed acceptance
- **THEN** the terminal plan identifies that work as an unclosed implementation
  batch
- **AND** the contract, status, and completion report do not claim that source,
  hosted CI, signatures, publication, runtime installation, or adopter
  conformance is already complete

#### Scenario: Superseded design advice is reconciled

- **WHEN** recovered guidance conflicts with a later accepted invariant
- **THEN** only the current invariant remains normative in the two canonical
  design authorities
- **AND** obsolete carrier advice is not restored as compatibility state,
  duplicated prose, or another tracked schema
