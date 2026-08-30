## ADDED Requirements

### Requirement: Git trust anchors use native host protection

ETHOS SHALL admit a repository-external Git trust anchor only when the host's
native authorization model proves that the anchor and its parent cannot be
modified by an untrusted identity. ETHOS-created anchors SHALL establish the
same protection that observation requires.

#### Scenario: POSIX anchor is owner-protected

- **WHEN** a trust anchor and its parent are not writable by group or other
  identities under the POSIX permission model
- **THEN** ETHOS admits the protection fact
- **AND** preserves the existing signature verification behavior.

#### Scenario: Windows anchor is ACL-protected

- **WHEN** a Windows trust anchor is owned by the current identity and its file
  and parent DACLs grant write-like authority only to the current identity or
  operating-system administrative identities
- **THEN** ETHOS admits the protection fact independent of emulated POSIX mode
  bits.

#### Scenario: Windows anchor is foreign-writable

- **WHEN** the anchor or its parent grants write-like authority to another
  principal, or native ACL facts cannot be obtained
- **THEN** ETHOS reports `git_object_trust_anchor_unprotected`
- **AND** does not infer protection from `chmod`, platform name, or successful
  signature verification alone.
