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

ETHOS SHALL expose bounded repair of explicitly selected incorrect commit identity or signature, the
rebuild of every declared ref's history with `--rebuild <record>`, its `--rollback` and `--release`,
and a keyless `--census`; `--corrections` SHALL stay separate. Readiness is effect-free. Authorized
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

#### Scenario: Each rebuild mode selects its own operation

- **WHEN** a request sets `--rebuild <record>`, with `--rollback`, `--release` or neither, and with
  or without `--apply`
- **THEN** it selects one of `lane.repair-signature.rebuild.preview`, `.rebuild.apply`,
  `.rollback.preview`, `.rollback.apply`, `.release.preview` or `.release.apply`, all placed before
  today's signature modes
- **AND** only the three applies take `--authorize` and `--expect-head`, only the rebuild apply also
  takes `--backup`, and only the rebuild preview and apply take `--key-stdin`

#### Scenario: A head is required only where an operation takes it

- **WHEN** a request omits `--expect-head`
- **THEN** readiness, the census and the rollback and release previews run without it
- **AND** the rebuild, rollback and release applies and today's signature modes refuse the request

#### Scenario: Only readiness and the apply read the key

- **WHEN** `--key-stdin` is given with `--rollback`, `--release` or `--census`
- **THEN** it refuses with `command_field_refused:key_stdin`
- **AND** `land --retag` and every reader of a rebuild take no key

#### Scenario: A rebuild changes only declared items

- **WHEN** an operator adds `--apply --authorize --expect-head <old> --backup <bundle> --key-stdin`
  to `--rebuild <record>` and the apply replaces commits
- **THEN** blobs, trees and messages change only by the record's declared items, and every rebuilt
  commit keeps its dates, authors, committers and parent order byte for byte under a current repair
  signature
- **AND** the apply reads the peers and changes none of them

#### Scenario: Re-entry after a rebuild

- **WHEN** rebuilt history contains an officially archived Change whose original held a declared
  item
- **THEN** archive resolution reads that Change's intent as the verified image of its original
- **AND** new proof, runtime binding and each peer publication are verified separately

#### Scenario: Rollback restores every declared old value

- **WHEN** an operator adds `--rollback --apply --authorize --expect-head <rebuilt old>` to
  `--rebuild <record>` before the owner deletes the old forge projects, also after the owner's gc
  and after `land --retag`
- **THEN** ETHOS fetches the declared old values from the side repository into the main object store
  as a separate write, never through the read-only attach
- **AND** it reverses each recorded re-tag plan and restores every declared ref inside one recorded
  `commit.identity-replace` intent

#### Scenario: A rollback preview re-observes the old peers

- **WHEN** an operator runs `ethos lane repair-signature --rebuild <record> --rollback`, without
  `--apply` or `--expect-head`
- **THEN** it selects `lane.repair-signature.rollback.preview`, compares each old peer with the
  record's expected per-peer states through the rebuild's peer reader and writes nothing
- **AND** a declared ref away from its recorded rebuilt value refuses by a fixed gap
- **AND** a peer whose state for a ref differs from the record's declared state blocks the preview
  by a fixed gap that names the ref and the peer

#### Scenario: Release previews, then waits for every receipt and recorded absence

- **WHEN** an operator runs `ethos lane repair-signature --rebuild <record> --release`, without
  `--apply` or `--expect-head`, then with `--apply --authorize --expect-head <rebuilt dev>`
- **THEN** the preview selects `lane.repair-signature.release.preview` and writes nothing, and the
  apply selects `lane.repair-signature.release.apply` and records each retired tag's absence that it
  observes and publication did not record
- **AND** the apply refuses until a publication receipt exists for each ref on each peer where the
  record says that peer held the ref and ETHOS publishes it, so `candidate/dev` needs none, and
  until each retired tag's absence is recorded
- **AND** it then deletes only the record's `rebuilt/` refs, in one recorded plan under its own
  lock, and a second run reports `already_applied`

#### Scenario: The rebuild applies are destructive under authorize

- **WHEN** `next_action` renders a rebuild apply, a rollback apply or a release apply of
  `ethos lane repair-signature`
- **THEN** `next.destructive` is true and its authorization is `authorize`
- **AND** none of them needs `--confirm-irreversible`, since the point of no return is the owner's
  deletion of the old forge projects, outside ETHOS
