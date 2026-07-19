## MODIFIED Requirements

### Requirement: Remote reconciliation continuation preserves historical carrier boundaries

When a historical remote-reconciliation carrier promoted its delta but lifecycle
work remains unfinished, ETHOS SHALL preserve the historical archive without
false completion and bind an active continuation to the same episode claim
before remaining closeout work proceeds. When the historical Work Lane cannot
be resumed in its original host worktree, the continuation SHALL retain only
context that can be freshly observed. It SHALL run in a distinct owned Work
Lane on a current candidate baseline and re-execute current proof rather than
treat historical proof or a reconstructed path as current authority.

#### Scenario: remaining lifecycle work continues after historical archival

- **WHEN** a historical reconciliation archive records unfinished local closeout, remote observation, or retirement work
- **THEN** an active continuation records the transfer and binds the episode claim
- **AND** it preserves normal merge and no-force constraints
- **AND** it distinguishes local proof, remote mutation, remote observation, and hosted-provider observation

#### Scenario: Historical worktree is absent

- **GIVEN** a historical Change, claim, and evidence stream remain readable
- **AND** the original host worktree or its checkout-local temporary state is
  absent
- **WHEN** a successor begins continuity work
- **THEN** it records retained source identities, irrecoverable state, current
  Git and Work Lane anchors, and a no-reconstruction boundary
- **AND** it leaves the historical lane and its archive observe-only
- **AND** it binds the existing episode claim to the active successor carrier
  before a new proof, land, closeout, or publication attempt.

#### Scenario: Current proof follows retained historical meaning

- **GIVEN** a successor continuity packet has preserved the historical meaning
- **WHEN** the successor reaches a stable committed HEAD
- **THEN** ETHOS evaluates current source and regressions through current
  OpenSpec lifecycle and HEAD-bound proof
- **AND** it distinguishes that proof from historical proof, temporary runtime
  state, hosted CI, and remote publication.
