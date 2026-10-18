# Change: Bound Retirement's Open-File Observation To Inspectable Processes

## Why

Reviewed-content retirement asks the native `lsof` observer which processes hold
the lane's files. On Linux, an unprivileged user cannot read the `/proc` entries
of another user's process, so `lsof` records each of them as a permission
failure, and the observer treats every such record as an incomplete
observation. A non-root runner always sees PID 1, so the GitHub hosted job fails
three reviewed-disposal cases on every run, and reviewed disposal is impossible
for any non-root Linux user. Darwin's `lsof` omits those processes silently, so
the same observation already completes there. A process that changes
credentials while `lsof` reads it also leaves one record unreadable, which made
GitLab verify fail one case at `f3d9f85e3`.

## What Changes

- The observation covers the processes the invoking user may inspect. On Linux,
  a process whose every record is a denied `/proc` entry is uninspectable, not
  incomplete, and is reported by process ID, user ID and command.
- A denial inside an otherwise inspected process, and any other unreadable
  record, still leaves the observation incomplete. Such a scan is taken again,
  at most three times within the observer's one 30-second timeout, before
  retirement blocks.
- Each content admission records its observation in the progress it produces;
  the terminal receipt and result carry the observation of the admission that
  removed the worktree. Darwin reports the uninspectable list as unavailable.
- The open-file observer moves from `ethos.adapters.process` to
  `ethos.adapters.open_files`, and `lsof` also reports each process's command
  and user ID.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: "Linked Work Lane retirement has one exact effect"
  narrows its permission failure to one inside an otherwise inspected process,
  adds the bounded rescan and adds the inspection boundary and its report.

## Impact

`src/ethos/adapters/open_files.py`, the retirement operation and its progress
contract, receipts, and their tests. Persisted progress gains an optional field,
so earlier receipts still read. Out of scope: privileged observation, and
running hosted jobs as root or in a container.
