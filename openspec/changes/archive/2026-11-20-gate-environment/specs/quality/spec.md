## ADDED Requirements

### Requirement: A proof result states the environment its declared commands inherit

A proof that executes gates SHALL state in `summary.environment` what its declared commands
inherit from the launch: the mode, the count of variables, the count outside the product's list
of kept names, the credential classes among them, whether the locked toolchain was read, the
locked tools that the launch path resolves outside their locked install, and the key names of
the Git configuration overlay. It SHALL hold no variable's value and SHALL NOT change a verdict,
a gap or an exit code.

#### Scenario: The launch carries credentials

- **WHEN** a proof executes from an environment that holds an SSH agent socket and a forge token
- **THEN** `summary.environment.credential_classes` holds `ssh-agent` and `forge-token`
- **AND** no member of the result holds the value of either variable

#### Scenario: The launch path resolves a locked tool elsewhere

- **WHEN** the repository locks a tool and the launch path resolves that tool's executable
  outside its locked install
- **THEN** `summary.environment.outside_lock` names the tool, in the Mise adapter's own code
- **AND** the proof's verdict is the one it has without the report

#### Scenario: The launch holds only kept names

- **WHEN** a proof executes from an environment that holds only names of the list, with a path on
  which no locked tool resolves outside the lock
- **THEN** `outside_allow_list` is zero, `credential_classes` is empty and `outside_lock` is empty

#### Scenario: The locked toolchain cannot be read

- **WHEN** the repository declares a locked toolchain that the Mise adapter cannot read
- **THEN** `summary.environment.locked_toolchain` is `unread:` followed by the adapter's code,
  or by the class of an error that carries none
- **AND** the gates run, and the verdict is the one it has without the report

#### Scenario: The repository declares no locked toolchain

- **WHEN** a proof executes in a repository without a Mise declaration
- **THEN** `locked_toolchain` is `undeclared` and `outside_lock` is empty

#### Scenario: The launch carries a Git configuration overlay

- **WHEN** the launch sets two keys through the indexed Git configuration variables
- **THEN** `git_overlay_keys` names both keys and holds neither value
- **AND** a key with a subsection is named by its section and its variable alone

#### Scenario: No gate executes

- **WHEN** a proof plans its gates without executing them, or a host observation is refused
  before its first gate
- **THEN** its summary has no `environment` member

### Requirement: A declared command's check names its executable and supplier

The check of each declared command SHALL name the executable that the proof started and its
supplier: `declared` for a path that the declaration names, `locked` for a locked install,
`host-baseline` for the host's own command directories, `launch-path` for any other directory of
the launch path, and `unresolved` when none was found. A provider gate's check SHALL name
neither.

#### Scenario: A bare tool name resolves on the launch path

- **WHEN** a declared command starts with a bare name that only a directory of the launch path
  holds, outside the lock and the host's command directories
- **THEN** its check names that file as the executable and `launch-path` as the supplier

#### Scenario: One command passes from two launches

- **WHEN** one declared command passes from two launches whose paths resolve its first word to
  different files
- **THEN** both results pass and name different executables

#### Scenario: A command names its own path

- **WHEN** a declared command starts with a path of the repository or with the bound interpreter
- **THEN** its check's supplier is `declared`

#### Scenario: A provider gate runs

- **WHEN** a gate that declares providers runs
- **THEN** its check names no executable and no supplier: both members are empty
