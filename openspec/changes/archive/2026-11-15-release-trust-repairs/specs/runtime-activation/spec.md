## MODIFIED Requirements

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

- **WHEN** the pinned release's class is `checksum` and the lock entry of the host's platform
  records its checksum and no provenance
- **THEN** the transition SHALL select its install as it selects an attested one

#### Scenario: A checksum-class pin has no locked checksum

- **WHEN** the pinned release's class is `checksum` and the lock entry of the host's platform is
  absent or records no checksum
- **THEN** the pinned release SHALL NOT be selected, and the transition SHALL name
  `runtime_pin_unattested`
- **AND** it SHALL keep a selection that is in place and refuse when there is none

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
