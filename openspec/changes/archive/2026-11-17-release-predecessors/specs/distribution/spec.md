## ADDED Requirements

### Requirement: A release records what it upgrades from

The release binding SHALL record under `[release.upgrade_from]` each release that the release
upgrades from, with its class, and SHALL name no repository there. `ethos lane upgrade-from` SHALL
derive that set offline for the committed release, report each subject's accepted head, pin,
selection and last bump without its path, count the subjects, and block when the record is
empty, lacks a derived release, or gives a release another class than its own.

#### Scenario: The record lists every derived release

- **WHEN** the committed binding records every release that the operation derives, each with its
  class
- **THEN** the operation passes and names no next action
- **AND** a recorded release that no subject names does not block.

#### Scenario: The record is absent or empty

- **WHEN** the committed binding declares no `[release.upgrade_from]`, or an empty one
- **THEN** the operation blocks with `release_upgrade_from_empty`
- **AND** its result still carries the derived releases with their classes.

#### Scenario: The record lacks a derived release

- **WHEN** a subject inside the support window pins or has selected a release that the record does
  not list
- **THEN** the operation blocks with `release_upgrade_from_incomplete:<releases>`, newest first.

#### Scenario: A recorded class is not the release's class

- **WHEN** the record names something other than one exact release, or gives a release a class
  other than the one its dispatch has
- **THEN** the operation blocks with `release_upgrade_from_invalid`
- **AND** its result still carries the derived releases with their classes.

#### Scenario: A subject selects a build that is no listed release

- **WHEN** a subject inside the support window pins or has selected a version that the changelog
  does not list, such as a development build
- **THEN** that version is no predecessor, and the operation refuses nothing for it
- **AND** the result names the version with the count of subjects that name it.

#### Scenario: The result counts the subjects

- **WHEN** the operation reads subjects inside the support window
- **THEN** its result states how many of them pin in each form, how many are subjects by their
  selection alone, how many recorded consumers and records could not be read, and how many
  installations record no consumer
- **AND** for the release itself and for each predecessor, how many subjects name it by their
  pin and how many by their selection alone, each subject once for a release.

#### Scenario: The changelog's history is invalid

- **WHEN** the releasing repository's changelog lists its releases out of order or names one
  twice
- **THEN** the operation blocks with the history's own errors and derives nothing.

#### Scenario: A refusal names its own repair

- **WHEN** the operation blocks for a gap that is not one of the record's
- **THEN** its next action does not ask for the record
- **AND** an operating system error is `release_upgrade_from_store_unreadable` with the error's
  name, and the result carries no path.

#### Scenario: The host records no consumer

- **WHEN** the host has no store of installations
- **THEN** the operation derives the previous release alone and reports no subject.

#### Scenario: The operation is a read

- **WHEN** `ethos lane upgrade-from --json` runs
- **THEN** it selects `lane.upgrade-from`, whose only effect is `read`, and exits 0 on every verdict
- **AND** its rows come newest bump first and carry no repository's name or path.

## MODIFIED Requirements

### Requirement: A beta's journey starts from every release that adopters select

A beta's journey evidence SHALL include an upgrade, with its rollback, from the previous release
and from every release that a subject pins or has selected. A subject is a governed repository
that the releasing host can read, that has selected a runtime of the product, and whose last
landed bump is inside the support window: at most 14 days before the newest landed bump read.
Release preparation SHALL derive those releases from the subjects' own trees and SHALL record no
count of subjects.

#### Scenario: A governed adopter selects an older release

- **WHEN** a subject inside the support window still pins or has selected a published release
  older than the previous release
- **THEN** a beta's journey evidence includes an upgrade from that release with its rollback
- **AND** without that evidence, the beta is not qualified for that subject.

#### Scenario: A subject falls outside the support window

- **WHEN** a subject's last landed bump is more than 14 days older than the newest landed bump
  among the subjects read
- **THEN** the releases that only it names are not derived
- **AND** the subject is reported as outside the window.

#### Scenario: Time alone moves no subject

- **WHEN** no subject lands a bump for longer than 14 days
- **THEN** every subject that was inside the support window stays inside it.

#### Scenario: A bump is read from the accepted branch

- **WHEN** a subject's accepted branch changed its pinned release and later changed its Mise
  configuration without moving the pin
- **THEN** its last landed bump is the commit that changed the pinned release
- **AND** a change of the pin's form that keeps the release is no bump.

#### Scenario: A subject declares no pin

- **WHEN** a recorded repository's accepted branch declares no pin, and the repository has
  selected a runtime
- **THEN** it is a subject by its selection, and the release it has selected is derived
- **AND** its last landed bump has no time, so it is inside the support window and the result
  gives its time as unknown.

#### Scenario: A subject's declared pin cannot be read

- **WHEN** a recorded repository's accepted branch declares a pin that cannot be read, such as
  two keys, a version prefix or text that is not TOML, and the repository has selected a runtime
- **THEN** it is a subject by its selection, inside the support window, and that pin names no
  release
- **AND** the result counts such pins by themselves, apart from the consumers that could not be
  read.

#### Scenario: A subject pins one release and has selected another

- **WHEN** a subject's accepted branch pins one release and the subject has selected another
- **THEN** both releases are derived, and the result shows the pin and the selection.

#### Scenario: A repository that cannot be read is no subject

- **WHEN** a recorded repository is gone, its record or its accepted branch cannot be read, or it
  neither pins a release nor has a selection that can be read
- **THEN** it is no subject, and the derivation refuses nothing for it
- **AND** the result counts the repositories and records that could not be read, each record
  once.

#### Scenario: A subject's selection cannot be read

- **WHEN** a recorded repository's accepted branch pins a release, and its selector cannot be
  read
- **THEN** it is a subject by its pin, and that selection names no release
- **AND** the result counts such selections by themselves, apart from the consumers that could
  not be read.

#### Scenario: A subject is frozen on its runtime

- **WHEN** a subject's owner froze it on a runtime, so that it takes no release
- **THEN** its recorded waiver names the subject's shape and its runtime, and no repository
- **AND** the condition that every subject is bumped does not count it
- **AND** its release stays a predecessor while its last landed bump is inside the support window.
