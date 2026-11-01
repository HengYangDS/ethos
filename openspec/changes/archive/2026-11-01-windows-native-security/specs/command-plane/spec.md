## MODIFIED Requirements

### Requirement: Git trust anchors use native host protection

ETHOS SHALL admit external Git trust anchors only when native host authorization protects the anchor
and parent from untrusted modification. Created anchors SHALL meet the same contract. Failed
establishment SHALL retain the bounded host reason. On Windows, ETHOS SHALL observe and establish
protection through the operating system's security API in its own process, without starting another
program.

#### Scenario: POSIX anchor is owner-protected

- **WHEN** a trust anchor and its parent are not writable by group or other identities under the
  POSIX permission model
- **THEN** ETHOS admits the protection fact
- **AND** preserves the existing signature verification behavior.

#### Scenario: Windows anchor is ACL-protected

- **WHEN** a Windows trust anchor is owned by the current identity and its file and parent DACLs
  grant write-like authority only to the current identity or operating-system administrative
  identities
- **THEN** ETHOS admits the protection fact independent of emulated POSIX mode bits.

#### Scenario: Windows parent shell exports an incompatible module path

- **WHEN** ETHOS observes or establishes Windows anchor protection from a parent process whose
  `PSModulePath` belongs to another PowerShell edition, with `PATH` narrowed to Git
- **THEN** it reads and writes the security descriptor without starting a child process
- **AND** the inherited environment neither changes the result nor is modified.

#### Scenario: Windows anchor is foreign-writable

- **WHEN** the anchor or its parent grants write-like authority to another principal, or has no DACL
- **THEN** ETHOS reports `git_object_trust_anchor_unprotected`
- **AND** does not infer protection from `chmod`, platform name, or successful signature
  verification alone.

#### Scenario: Windows security facts are unavailable

- **WHEN** the security descriptor of the anchor or its parent cannot be read, or holds an access
  entry that ETHOS cannot classify
- **THEN** ETHOS reports `git_object_trust_anchor_observation_unavailable` with the failed call and
  native error number
- **AND** does not admit the anchor.

#### Scenario: Windows protection operation fails

- **WHEN** the native Windows operation cannot establish the required DACL
- **THEN** ETHOS fails closed with `git_object_trust_anchor_protection_failed`
- **AND** preserves the failed call, native error number and bounded native error text.
