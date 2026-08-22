## MODIFIED Requirements

### Requirement: Accepted-root closeout is bound to one audited candidate HEAD

ETHOS SHALL bind candidate audit, signature, local or external proof admission,
prepared ref intent, exact compare-and-swap, post-image observation, and
Attestation to one observed candidate commit and tree. Dry-run and apply SHALL
consume the same typed resolution; Git hooks and other projections SHALL not
own a competing accepted-head decision.

#### Scenario: Candidate HEAD changes during or after closeout audit

- **WHEN** accepted-root closeout observes the candidate HEAD before audit
- **THEN** the audit receives that HEAD and tree as its claim binding
- **AND** closeout re-observes the candidate after audit and immediately before
  mutation
- **AND** any mismatch blocks proof admission and accepted-root movement.

#### Scenario: Exact external evidence is bound before admission

- **WHEN** a package-only caller supplies an external verification receipt for
  the candidate
- **THEN** ETHOS validates its commit, tree, action, proof-floor digest, policy
  digest, implementation digest, issuer, key, signature, and validity against
  the exact closeout subject
- **AND** stale, failed, forged, wrong-subject, wrong-role, or wrong-verifier
  evidence fails closed
- **AND** a valid receipt remains an admission fact and never mints mutation
  authority.

#### Scenario: Local-only profile admits without Forge facts

- **WHEN** the repository profile declares no Forge peer and local proof is the
  selected proof plane
- **THEN** the same closeout transaction admits the exact locally proved signed
  candidate head
- **AND** no hosted receipt, provider status, or remote truth is fabricated.

