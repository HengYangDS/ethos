## MODIFIED Requirements

### Requirement: Result projection preserves diagnostic execution facts

When a command cannot resolve or execute a required tool or projection, the owning resolution SHALL
preserve the exact boundary facts needed to recover, including the attempted binary or route, cwd,
captured stderr of a local tool or projection, and relevant environment projection. A peer
observation's failure SHALL carry its exact command, cwd and exit status without the remote's
stderr. A projection failure SHALL NOT be relabeled as adoption failure or product-test failure.

#### Scenario: Official projection is unavailable from the working tree

- **WHEN** official OpenSpec artifacts exist but the selected projection cannot be read
- **THEN** the result identifies the exact OpenSpec command, cwd, exit status, and stderr
- **AND** the sole next action repairs or completes that projection rather than running
  `ethos adopt`

#### Scenario: A continuation route is unsupported

- **WHEN** a continuation token is sent to the wrong execution route or a capability is unavailable
- **THEN** the structured result distinguishes wrong route, unavailable capability, and provider
  finalization failure
- **AND** it states whether mutation occurred and names the sole safe continuation without replaying
  the mutation

#### Scenario: A local tool keeps its stderr

- **WHEN** a local tool or projection that a command requires fails
- **THEN** the result carries the attempted binary or route, cwd, exit status and the tool's
  captured stderr

#### Scenario: A peer observation omits the remote's stderr

- **WHEN** an observation of a peer's refs fails
- **THEN** the result carries the exact command, cwd and exit status, and none of the remote's
  stderr, which can echo a private host or path

### Requirement: Accepted signature repair command

ETHOS SHALL expose bounded repair of explicitly selected incorrect commit identity or signature,
the readiness of a rebuild of every declared ref's history with `--rebuild <record>`, and a keyless
`--census`; `--corrections` SHALL stay separate. Readiness is effect-free. Authorized
application SHALL preserve non-selected content, retain verifiable originals, re-sign affected
objects and apply exact selected refs. Historical evidence SHALL NOT be relabeled current.

#### Scenario: Exact selection and backup

- **WHEN** an operator requests signature or identity repair
- **THEN** readiness reports exact old identities, affected descendants and ref scope
- **AND** application requires unchanged coordinates and a verified recovery copy

#### Scenario: Only authorized bytes change

- **WHEN** signature or identity repair replaces commits
- **THEN** trees, messages, timestamps and unselected identities remain unchanged
- **AND** parent order follows the verified mapping with current repair signatures

#### Scenario: Stale or interrupted repair

- **WHEN** refs drift or an effect acknowledgement is lost
- **THEN** repair rejects stale state or observes durable results before retry
- **AND** no unrelated refs or worktrees are rewritten

#### Scenario: Re-entry after repair

- **WHEN** history that a signature or identity repair rewrote contains an officially archived
  Change
- **THEN** validated repair provenance preserves its exact intent bytes
- **AND** new proof, runtime binding and each peer publication are verified separately

#### Scenario: Continued history retains archived intent

- **WHEN** later commits descend from a completed repair or a sequence of completed repairs
- **THEN** archive resolution follows validated object mappings and native ancestry
- **AND** it preserves the original archive acceptance without requiring the current HEAD to be a
  repair result
- **AND** missing effect evidence or ambiguous replacement paths cannot supply archive authority

#### Scenario: Readiness has no signing effect

- **WHEN** an operator requests signature-repair readiness for an exact accepted head
- **THEN** ETHOS reports current prerequisites and the authorized apply action
- **AND** it does not create a replacement object or move refs or worktrees

#### Scenario: Application requires authorization

- **WHEN** repair application lacks explicit authorization or has stale coordinates
- **THEN** it rejects the request before creating a replacement object
- **AND** it identifies the failed boundary and one fresh next action

#### Scenario: Successful repair requires new proof

- **WHEN** the selected local repair effects finish and their postconditions hold
- **THEN** the result identifies the replacement commit and exact reproof command
- **AND** it does not claim proof, runtime activation or remote publication

#### Scenario: Recovery observes instead of repeating effects

- **WHEN** a signing or ref effect has completed but its acknowledgement was lost
- **THEN** recovery uses durable result evidence and current Git observations
- **AND** it does not create another replacement or repeat completed effects
- **AND** missing evidence remains unknown rather than implying completion

#### Scenario: Rebuild readiness reports by count

- **WHEN** an operator runs `ethos lane repair-signature --rebuild <record> --key-stdin`, without
  `--apply` or `--expect-head`
- **THEN** it selects `lane.repair-signature.rebuild.preview` and reports rebuild readiness by count
  and fixed gap name only
- **AND** it creates no object, record or side repository and moves no ref or worktree

#### Scenario: The census needs no record and no key

- **WHEN** an operator runs `ethos lane repair-signature --census`
- **THEN** it selects `lane.repair-signature.census`, which comes first, and reports counts by form
  and ref class, read-only
- **AND** `--rebuild`, `--key-stdin` or `--apply` beside `--census` refuses with
  `command_field_refused:<field>`

#### Scenario: A head is required only where an operation takes it

- **WHEN** a request omits `--expect-head`
- **THEN** rebuild readiness and the census run without it
- **AND** today's signature modes refuse the request

#### Scenario: Only rebuild readiness reads the key

- **WHEN** `--key-stdin` is given with `--census`
- **THEN** it refuses with `command_field_refused:key_stdin`
