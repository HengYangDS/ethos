## MODIFIED Requirements

### Requirement: Candidate proof admission selects repository authority

ETHOS SHALL use one repository-transition proof query for readiness and mutation.
The query SHALL bind the exact repository identity, HEAD, tree, proof policy and
applicable Commitment authority before resolving mutable dependencies or proof
conflicts. Candidate acceptance, accepted publication, and control-replacement
admission SHALL consume that query rather than maintaining command-specific
selectors.

#### Scenario: Historical Work Lane proof is not applicable

- **GIVEN** one exact HEAD has both a repository-Commitment proof and a proof
  authorized by an archived Change Commitment for the same repository
- **WHEN** a repository role transition is evaluated
- **THEN** ETHOS selects the repository-Commitment proof
- **AND** the archived proof remains queryable but does not invalidate the
  transition.

#### Scenario: Retired Work Lane leaves the only applicable proof

- **GIVEN** an archived Change proof is bound to the exact repository, HEAD,
  tree and current proof policy
- **AND** its former Work Lane generation is no longer current
- **WHEN** no repository-Commitment proof exists for that HEAD
- **THEN** the repository-transition query may select the archive-authorized
  proof
- **AND** it does not require recreating or deleting historical lane evidence.

#### Scenario: Applicable proof conflict fails closed

- **GIVEN** two current proofs under the authority selected for the query
- **WHEN** their exact bindings or assertions differ
- **THEN** ETHOS returns the stable mismatch coordinate
- **AND** no repository effect is authorized.

#### Scenario: Closeout readiness and apply share proof admission

- **WHEN** accepted-root closeout is evaluated without and with `--apply`
- **THEN** both evaluations query the same candidate HEAD and repository
  Commitment through the same repository-transition proof selector
- **AND** a proof-selection mismatch cannot appear only after apply is requested.

#### Scenario: Wrong authority cannot satisfy candidate acceptance

- **WHEN** a proof names another repository or does not bind the exact HEAD,
  tree, policy, or applicable authority
- **THEN** ETHOS rejects it with a specific mismatch coordinate
- **AND** does not infer authority from another proof on the same HEAD.
