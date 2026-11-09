## ADDED Requirements

### Requirement: Lane redaction answers unknown without a known feed

When the feed that the clone can know is incomplete, every mode of
`ethos lane redact private-addresses` SHALL answer `unknown` with the feed's gaps before it
validates or uses a key. The preview SHALL still list what it reads, and the apply and the verify
SHALL write nothing and record nothing.

#### Scenario: The feed is not known

- **WHEN** the publication declaration is invalid, a declared peer's remote holds no URL, or
  nothing is fed
- **THEN** the preview, the apply and the verify answer `unknown` with the declaration's gaps,
  with `peer_identity_feed_unreadable:<remote>` or with `peer_identity_feed_empty`
- **AND** the apply writes nothing and the verify records no `redaction:private-peer`
