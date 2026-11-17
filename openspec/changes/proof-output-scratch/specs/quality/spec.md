## ADDED Requirements

### Requirement: A declared command names the scratch of its run

A declared command MAY name `{scratch}` in an argument. ETHOS SHALL replace it at launch with one
directory under the temporary root that every command of the same run of gates receives, mark its
root with the owner's record where the run holds a host ticket and declares an actor, and remove
it when the run ends. The gate's execution identity SHALL keep the placeholder. A command that
does not name it SHALL be launched as before.

#### Scenario: A declared command names the scratch

- **WHEN** a gate's command holds `{scratch}` in an argument
- **THEN** the launched command receives a directory outside the lane in its place
- **AND** every command of the run receives the same directory
- **AND** the gate's execution identity keeps the placeholder

#### Scenario: A declared command does not name the scratch

- **WHEN** no command of a run holds `{scratch}`
- **THEN** each command's arguments, working directory and environment are those of the release
  before
- **AND** no scratch directory is made

#### Scenario: The run ends

- **WHEN** a run of gates whose commands named the scratch has ended
- **THEN** the directory and its root are removed

#### Scenario: Native evidence binds the launch

- **WHEN** a gate that declares native outputs also names `{scratch}`
- **THEN** its evidence is admitted only with the arguments of its own launch, the scratch and the
  output root in the placeholders' places

### Requirement: A proof reports what its attempt left in the lane

A proof that executes its gates, full or focused, SHALL observe the lane's nontracked paths before
its first gate and after its last. It SHALL report, for the evidence and artifact homes of the
artifact topology, the files and bytes that appeared or changed, the new names under the work
home, and each new nontracked root. The report SHALL NOT change the proof's verdict, exit or
required gaps.

#### Scenario: A gate writes a report into the lane

- **WHEN** a declared command writes a file under an evidence home during a proof
- **THEN** the proof's result reports that home with the file's bytes

#### Scenario: Nothing is left

- **WHEN** no gate of an attempt writes a nontracked path that the observation reads
- **THEN** the report is empty

#### Scenario: A report does not decide the proof

- **WHEN** two attempts differ only in what a gate left in the lane
- **THEN** their verdicts, states and required gaps are equal

#### Scenario: A write inside an ignored root

- **WHEN** a gate writes inside an environment or a tool cache that Git lists whole
- **THEN** the report does not list it
- **AND** an empty report is not a statement that the lane is unchanged

#### Scenario: The lane cannot be listed

- **WHEN** Git's listing of the lane fails before or after the gates
- **THEN** the report names that it is unavailable and holds nothing else

#### Scenario: Many paths appeared

- **WHEN** the report is larger than the result's payload bound
- **THEN** the bounded result keeps the files and bytes of each class of home
- **AND** the paths are in the result's detail
