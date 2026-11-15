## ADDED Requirements

### Requirement: One owner gives every journey child a fresh environment

One environment owner SHALL give every child process of the release journey a new home and
temporary directory, Git without system or global configuration, system attributes or templates,
and a path of one link for each declared executable. No agent socket, desktop variable or other
host variable SHALL reach a child, except the forge token and the tool supply's location in
acquisition, as the scenarios bound them. The journey SHALL run the Mise executable whose digest
the repository binds.

#### Scenario: A child inherits or is handed its environment

- **WHEN** a journey stage starts a child that inherits the stage's environment, or one that is
  handed it
- **THEN** the child SHALL see the stage's own home, temporary directory, Git configuration file
  and template directory, all new and empty
- **AND** its path SHALL resolve the declared executables and no other

#### Scenario: The host holds credentials and a desktop session

- **WHEN** the host's environment holds an agent socket, a forge token or a desktop variable
- **THEN** no stage's process SHALL hold any of them, and no child SHALL inherit one
- **AND** acquisition SHALL hand the forge token to the forge's client and to Mise's lock and
  install of a pin, and to no other child

#### Scenario: Acquisition finds the host's tool supply

- **WHEN** the host's environment says where its tool supply is
- **THEN** acquisition's own process SHALL keep those variables, and a child that is handed its
  environment SHALL NOT receive them
- **AND** qualification's process SHALL NOT keep them

#### Scenario: The host installed another Mise

- **WHEN** the host's path holds a Mise executable
- **THEN** the journey SHALL run the executable of the repository's tool supply, whose digest the
  repository binds, and not the host's

#### Scenario: A fixture adopter is built

- **WHEN** the journey creates a fixture adopter and its signed commits
- **THEN** each of those Git commands SHALL run in the stage's environment

#### Scenario: A stage ends

- **WHEN** a stage ends, passing or not
- **THEN** the journey's own process SHALL hold the host's environment again

#### Scenario: A Windows host runs a stage

- **WHEN** a stage runs on Windows
- **THEN** its children SHALL receive the Git variables over the install smoke's minimal
  environment, and the home, temporary directory and path SHALL stay the host's

### Requirement: Acquisition is the journey's only networked stage

The release journey SHALL run as two stages. Acquisition, the only stage that reaches the network,
SHALL verify the prerelease and each predecessor, prove each release's exact GitHub pin, and write
a manifest of the archives it verified. Qualification SHALL read that manifest alone, check its
environment before it starts a child, hash each archive again before it installs it offline, and
run every journey step. Each leg's receipt SHALL name its venue.

#### Scenario: Acquisition completes

- **WHEN** acquisition has verified each release by its class and Mise has locked, installed and
  refused the rebound locks of the prerelease's pin
- **THEN** it SHALL write a manifest that names, the prerelease first, each release's version,
  class, archive and SHA-256
- **AND** it SHALL remove what the pins installed

#### Scenario: Qualification's environment shows more than was declared

- **WHEN** qualification's environment holds a variable that was not declared, lacks or changes a
  declared one, holds a home, temporary directory, template directory or Git configuration that
  is not empty, or holds a path entry that is not one link to an existing declared executable
- **THEN** the leg SHALL fail with `journey_environment_not_hermetic:<what>` before its first
  child

#### Scenario: An archive changed after acquisition

- **WHEN** an archive's SHA-256 differs from the one its manifest entry records
- **THEN** the leg SHALL fail with `release_journey_archive_tampered:<archive>` before Mise
  installs it

#### Scenario: The manifest is not whole

- **WHEN** the manifest is absent, unparsable or empty, an entry lacks a field or adds one, or an
  archive lies outside the manifest's directory
- **THEN** the leg SHALL fail with `release_journey_manifest_invalid` before any install

#### Scenario: Qualification installs a release

- **WHEN** qualification installs the prerelease or a predecessor
- **THEN** Mise SHALL install the acquired archive in offline mode from a local table, in the
  layout that the pin installs

#### Scenario: A leg records where it ran

- **WHEN** a leg writes its receipt
- **THEN** `venue` SHALL read `ci` under a CI runner and `local` otherwise

## MODIFIED Requirements

### Requirement: A hosted journey qualifies each published prerelease

After a release run publishes a prerelease, a hosted journey SHALL install it through the exact
GitHub pin, with provenance verification, on macOS and Linux. From the archives that this
acquisition verified it SHALL then pass, in fixture adopters on fresh host stores, a cold install,
host-store pinning, hook binding, a full proof and status, an upgrade from each predecessor with
its rollback, and uninstall. A dispatch SHALL run the journey alone for an already published
prerelease.

#### Scenario: A prerelease is published

- **WHEN** a release run publishes a prerelease
- **THEN** the journey runs on macOS and Linux against its published assets
- **AND** each leg's receipt names the result of every journey step.

#### Scenario: A published prerelease is qualified again

- **WHEN** a dispatch names an already published prerelease for the journey alone
- **THEN** only the journey runs, and the release is not published again.

#### Scenario: Each leg installs through the pin

- **WHEN** a leg acquires the prerelease or one of its predecessors
- **THEN** it locks the exact GitHub pin of that release and installs its own platform from the lock
- **AND** its receipt names the Mise release, each release's class and each lock's format version.

#### Scenario: The steps run on the acquired archives

- **WHEN** a leg runs the cold install, an upgrade or the uninstall
- **THEN** the release it installs is the archive that acquisition verified, installed offline
- **AND** the installation that the pin made is not the one the steps run on.
