## ADDED Requirements

### Requirement: Store byte budgets report and never refuse

The preview of `ethos hook retire-records` SHALL report the files and bytes under each top-level
name of the Git-common store, the time of the read, and the owned kinds' bytes against
`retention.status_bytes`. The preview of `ethos hook retire-supply` SHALL report the host store's
installations against `retention.host_bytes`. A budget row SHALL be `within`, `over`, or `unread`
with a count, and SHALL NOT be `within` on an incomplete read.

#### Scenario: A store is within its budget

- **WHEN** the owned kinds hold fewer bytes than `retention.status_bytes`
- **THEN** the preview's summary reports those bytes, the budget and `within`

#### Scenario: A store is over its budget

- **WHEN** the owned kinds hold more bytes than the budget
- **THEN** the row reports `over`
- **AND** the preview's verdict, state, required gaps and next action equal those of the same
  store under a higher budget

#### Scenario: A place of the store cannot be read

- **WHEN** the read cannot reach an owned directory, or a directory or a file's status below one
- **THEN** the row reports the count of such places and is never `within`: it is `over` when the
  bytes that were counted already exceed the budget, and `unread` otherwise
- **AND** the preview's verdict, state, required gaps and next action stay what they were

#### Scenario: A binding declares its own value

- **WHEN** the accepted branch's binding declares a lower `retention.status_bytes`
- **THEN** the row is judged against the declared value

#### Scenario: The store holds a link

- **WHEN** a directory of the store holds a symbolic link
- **THEN** the report counts regular files by their own sizes and follows no link

#### Scenario: The host store is reported

- **WHEN** the preview of `ethos hook retire-supply` runs, with or without `--release-absent`
- **THEN** its summary reports the bytes of the host store's installations against
  `retention.host_bytes`
