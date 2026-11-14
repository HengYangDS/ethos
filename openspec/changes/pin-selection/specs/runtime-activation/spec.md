## ADDED Requirements

### Requirement: Runtime activation follows the accepted pin forward

Without `--runtime`, hook activation and `adopt --select-runtime` SHALL read the exact GitHub pin
and its lock entry from the accepted branch and SHALL select that release's installed runtime only
when it is newer than `CURRENT`. In any other state they SHALL leave `CURRENT` in place and name the
state, or refuse by that name when nothing is selected. Without a pin they SHALL select the invoking
build. ETHOS SHALL fetch nothing.

#### Scenario: A newer pin is installed

- **WHEN** the accepted branch pins a release newer than `CURRENT`, the lock entry of the host's
  platform records `github-attestations` and Mise holds that release's install
- **THEN** the transition SHALL select that install through the declaration preflight and the host
  store
- **AND** it SHALL report the pin as followed

#### Scenario: No pin is declared

- **WHEN** the accepted branch declares no exact GitHub pin
- **THEN** the transition SHALL select the invoking build and report `runtime_pin_absent`

#### Scenario: The pin is older than the selection

- **WHEN** the accepted pin names a release older than `CURRENT`
- **THEN** `CURRENT` SHALL stay and the transition SHALL report `runtime_pin_behind_current`
- **AND** its next action SHALL name `hook install --runtime` with `--reason` from a lane

#### Scenario: The lock entry is unattested

- **WHEN** the pinned release is outside the checksum class and the lock entry of the host's
  platform is absent or records no `github-attestations`
- **THEN** the pinned release SHALL NOT be selected, and the transition SHALL name
  `runtime_pin_unattested`
- **AND** it SHALL keep a selection that is in place and refuse when there is none

#### Scenario: A checksum-class release is pinned

- **WHEN** the pinned release's class is `checksum` and its lock entry records no provenance
- **THEN** the transition SHALL select its install as it selects an attested one

#### Scenario: The pinned release is not installed

- **WHEN** Mise holds no install of the pinned release
- **THEN** `CURRENT` SHALL stay and the transition SHALL name `runtime_pin_not_installed`, with
  `mise install --locked` as its next action
- **AND** ETHOS SHALL install and fetch nothing

#### Scenario: A development build of the pinned release is selected

- **WHEN** `CURRENT` is a development build of the release that the accepted branch pins
- **THEN** the pinned release SHALL count as newer and the transition SHALL select its install

#### Scenario: The pin cannot be read

- **WHEN** the accepted configuration names the pin in a form that its reader refuses
- **THEN** the transition SHALL keep `CURRENT` and name the reader's gap

### Requirement: A lane-bound selection receipt holds a departure

From a Work Lane, `hook install --runtime <R> --reason <text>` for a release other than the accepted
pin SHALL write and read back a receipt of kind `successor` or `rollback` under
`<git-common>/ethos/receipts/runtime-selection/`, after the declaration preflight and before any
other effect. While the accepted pin and the lane's ref last and `CURRENT` is R, a transition SHALL
keep `CURRENT` and report `runtime_selection_open`. Without a reason or a lane the command SHALL
refuse.

#### Scenario: A lane selects a successor

- **WHEN** a lane runs `hook install --runtime <R> --reason <text>` for a release newer than the
  accepted pin
- **THEN** the receipt SHALL have kind `successor` and name the pin, the release, the runtime's
  digest, the lane and the reason
- **AND** the next transition SHALL keep `CURRENT` on R and report `runtime_selection_open`

#### Scenario: A lane rolls back

- **WHEN** a lane runs that command for a release older than the accepted pin
- **THEN** the receipt SHALL have kind `rollback`
- **AND** the next transition SHALL keep `CURRENT` on R instead of moving forward to the pin

#### Scenario: The accepted pin changes

- **WHEN** the accepted branch pins another release while a receipt is open
- **THEN** the next transition SHALL delete the receipt and follow the pin forward

#### Scenario: The lane retires

- **WHEN** the lane's ref is gone while its receipt remains
- **THEN** the next transition SHALL delete the receipt
- **AND** a `CURRENT` newer than the pin SHALL stay, reported as `runtime_pin_behind_current`

#### Scenario: A departure has no reason or no lane

- **WHEN** `hook install --runtime` names a release other than the accepted pin without `--reason`,
  or from a root that is not a Work Lane
- **THEN** it SHALL refuse with `runtime_selection_receipt_required` and change nothing
- **AND** its next action SHALL name the command with `--reason` from a lane

#### Scenario: The selection is no departure

- **WHEN** `hook install --runtime` names the pinned release, or the accepted branch declares no pin
- **THEN** activation SHALL need no reason and write no receipt

## MODIFIED Requirements

### Requirement: A rollback across a repaired declaration refuses until restored

Hook activation SHALL probe the target runtime against the root's tree before it pins anything,
whenever `--runtime` names a build other than the invoking one. When the target refuses the tree's
publication declaration, it SHALL refuse with `runtime_rollback_declaration_repaired`, leave no
effect and name restoring the predecessor's declaration in a lane as next. It SHALL hold as
`ROLLBACK` only a predecessor that an install of the root can admit; status SHALL report a held
one that none can.

#### Scenario: A selector-only rollback after the repair

- **WHEN** an operator activates the ROLLBACK runtime on a tree whose declaration the repair changed
- **THEN** activation refuses with `runtime_rollback_declaration_repaired`
- **AND** selectors, hooks and state are unchanged

#### Scenario: A rollback after the restore

- **WHEN** a lane restores the predecessor's declaration and its HEAD contains the accepted tip
- **THEN** activating ROLLBACK on that lane succeeds

#### Scenario: A predecessor that no install would admit

- **WHEN** the root's accepted source names the one build an install admits and a cutover's
  predecessor is another build
- **THEN** activation SHALL neither pin the predecessor into the host store nor write `ROLLBACK`
- **AND** its result SHALL report the predecessor as unrunnable, with the gap the install would name

#### Scenario: A held rollback can no longer run

- **WHEN** status reads a `ROLLBACK` whose runtime's manifest is gone or unreadable, or whose build
  the root's accepted source does not admit
- **THEN** status SHALL report it as unrunnable, with that gap and one next action: the CURRENT
  runtime's `hook install` for the root
- **AND** that install SHALL stop holding the rollback and report what it released
