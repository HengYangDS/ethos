## ADDED Requirements

### Requirement: A readiness run names what it did not examine

The result of `ethos prove --readiness --execute` SHALL name, beside the gates it did not run, the
tests that read what its Work Lane changed, the changed paths that no test reads, and each
task-runner session that only a Forge job asks for. The report SHALL refuse nothing and SHALL
change no verdict. A part that cannot be read SHALL be named as unavailable. ETHOS SHALL run none
of the tests it names.

#### Scenario: A Work Lane changes a path that a test reads

- **WHEN** a readiness run executes on a Work Lane whose commits since the candidate branch change
  a path
- **THEN** `data.unexamined.tests` maps each test that reads the path to its reason
- **AND** `data.unexamined.base` names the candidate branch and no selected test is run

#### Scenario: A changed path has no reader

- **WHEN** no test reads a path that the Work Lane changed
- **THEN** `data.unexamined.unread_paths` lists that path
- **AND** the verdict is what the readiness gates decide

#### Scenario: The checkout is not a Work Lane

- **WHEN** a readiness run executes on any other branch role
- **THEN** `data.unexamined.base` is empty and no test is selected
- **AND** the sessions that only a Forge job asks for are still listed

#### Scenario: Only a Forge job asks for a session

- **WHEN** a step of a pipeline file asks the task runner for a session that no planned gate's
  command asks for
- **THEN** `data.unexamined.forge_only_sessions` maps that session to the jobs that ask for it
- **AND** a session that a planned gate's command also asks for is not listed
- **AND** `data.unexamined.forge_jobs` counts the jobs that were read

#### Scenario: A part cannot be read

- **WHEN** the candidate branch does not resolve, or a tracked pipeline file cannot be read
- **THEN** `data.unexamined.unavailable` names that part with its reason
- **AND** the other part is reported, and the verdict is what the readiness gates decide

### Requirement: A change selects the tests that read it from tracked text

A selection SHALL give each selected Python test one reason: the test changed; a changed
`conftest.py` is in a directory above it; it imports a changed file or a file that imports one; its
text names a changed path; or its text names the wheel's carried-file table and that table carries
a changed path. A test that several reasons select SHALL keep the first of them in this order. A
selection SHALL be a lower bound and SHALL NOT be reported as a proof.

#### Scenario: A changed document is named by a test

- **WHEN** a changed document's path stands in the text of a test that imports no changed file
- **THEN** the test is selected with the reason `names`

#### Scenario: A changed file is carried by the package

- **WHEN** the wheel's `force-include` table names a changed path, or a directory above it
- **THEN** each test whose text names that table is selected with the reason `stages`
- **AND** a changed path that the table does not name selects no test by this reason

#### Scenario: A changed Python file is imported

- **WHEN** a test imports a changed Python file, or imports a file that imports it
- **THEN** the test is selected with the reason `imports`
- **AND** a test that reaches the changed file only through two imported files is not selected

#### Scenario: A test or a conftest changes

- **WHEN** a test changes, or a `conftest.py` changes
- **THEN** the test is selected with the reason `changed`
- **AND** each test in the directory of the changed `conftest.py`, or below it, is selected with the
  reason `conftest`

#### Scenario: A file cannot be parsed

- **WHEN** a Python file of the repository does not parse
- **THEN** its imports select nothing, and its text is still read for the names of changed paths
