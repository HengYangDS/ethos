## ADDED Requirements

### Requirement: CI commit trust has one released binding operation

`ethos hook bind-trust` SHALL bind the commit trust that a job's operator supplies to the checkout's
local `gpg.ssh.allowedSignersFile`: a protected file outside the checkout, named by `--anchor` or
`ETHOS_COMMIT_TRUST_ANCHOR`, or the public material in `ETHOS_COMMIT_ALLOWED_SIGNERS`. It SHALL
preview by default, write only with `--apply`, read the setting back, and SHALL NOT create a key,
change an identity or take trust from the candidate.

#### Scenario: A preview names the anchor and writes nothing

- **WHEN** `ethos hook bind-trust --anchor <path> --json` names a protected file outside the
  checkout
- **THEN** the result names that file, and its next step is the apply request
- **AND** no Git configuration and no file is written

#### Scenario: An apply binds the one supplied input

- **WHEN** `ethos hook bind-trust --apply` runs with exactly one input
- **THEN** the local `gpg.ssh.allowedSignersFile` names the validated anchor, which the operation
  reads back, and no other setting changes
- **AND** supplied material is bound from a new temporary file that only the current identity and
  the host's administrators can write

#### Scenario: More than one input is ambiguous

- **WHEN** more than one of `--anchor`, `ETHOS_COMMIT_TRUST_ANCHOR` and
  `ETHOS_COMMIT_ALLOWED_SIGNERS` is supplied
- **THEN** the operation refuses with `ci_commit_trust_inputs_ambiguous` and binds nothing

#### Scenario: No input is supplied

- **WHEN** no input is supplied
- **THEN** the operation passes with the state `unbound` and binds nothing
- **AND** commit verification still refuses a missing required anchor

#### Scenario: An input or its binding is refused

- **WHEN** the anchor is missing, relative, inside the checkout or writable by an untrusted
  identity, the material is blank, or the read-back does not name the anchor
- **THEN** the operation refuses with the anchor's own gap, `ci_commit_trust_material_missing` or
  `ci_commit_trust_projection_failed`, and exits 1
- **AND** it leaves no temporary anchor behind

#### Scenario: A hosted job binds trust before it admits a range

- **WHEN** a hosted job of the product repository bootstraps on either forge
- **THEN** it runs `ethos hook bind-trust --apply` before any `ethos hook commit-range` step
- **AND** no step runs a module that a release does not ship to bind trust
