## MODIFIED Requirements

### Requirement: Lane redaction writes peer markers only in effective record roots

`ethos lane redact private-addresses` SHALL preview without a key and print no value. Its apply,
with `--key-stdin`, `--authorize` and the lane head, SHALL write markers and numbers only in the
effective record roots of the working tree, under prewrite and the Lease. Its verify SHALL re-derive
every marker and number from the base revision and record `redaction:private-peer` on a pass.
When the feed is not known, every mode SHALL answer `unknown` with the feed's gaps before it
validates or uses a key: the preview still lists what it reads, and the apply and the verify
write and record nothing.

#### Scenario: The preview names occurrences, not values

- **WHEN** the tracked tree holds fed literals inside and outside the effective record roots
- **THEN** the preview lists each one's file, line, form and root membership and counts those
  outside, and prints no host, port, path or ID

#### Scenario: An apply refuses what it cannot replace

- **WHEN** the lane head moved, or an occurrence is `manual`, such as an unfed path after a fed host
- **THEN** the apply refuses and writes nothing

#### Scenario: A redacted record keeps its digests

- **WHEN** the apply redacts a file whose SHA-256 a record in the same commit holds
- **THEN** the record holds the redacted file's digest

#### Scenario: Verify records the redaction

- **WHEN** every marker and number of the head re-derives from the base with the key
- **THEN** `redaction:private-peer` records base, head, roots, count and the key generation
- **AND** a key of another generation refuses with `redaction_key_generation_changed` unless
  `--rotate` is given

#### Scenario: The feed is not known

- **WHEN** the publication declaration is invalid, a declared peer's remote holds no URL, or
  nothing is fed
- **THEN** the preview, the apply and the verify answer `unknown` with the declaration's gaps,
  with `peer_identity_feed_unreadable:<remote>` or with `peer_identity_feed_empty`
- **AND** the apply writes nothing and the verify records no `redaction:private-peer`
