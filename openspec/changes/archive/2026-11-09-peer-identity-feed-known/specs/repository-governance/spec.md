## ADDED Requirements

### Requirement: A push refuses a peer identity feed that the clone cannot know

Under `peer_identity.mode = "required"`, push admission SHALL refuse a feed that the clone cannot
know before it reads the advertisement: an invalid publication declaration with its own required
gaps, else each declared peer whose remote holds no URL in its `url` or `pushurl` keys as
`peer_identity_feed_unreadable:<remote>`, else a feed of nothing as `peer_identity_feed_empty`. A
remote that marks itself `forgePrivate` SHALL feed whether or not the declaration names it.

#### Scenario: The clone cannot know its protected peers

- **WHEN** the trusted commit's profile declares `required` and the publication declaration is
  invalid, a declared peer's remote holds no URL, or nothing is fed
- **THEN** push admission refuses with the declaration's gaps, with
  `peer_identity_feed_unreadable:<remote>` or with `peer_identity_feed_empty`, and reads no
  advertisement
- **AND** an unread peer is named even when another declared peer is read

#### Scenario: An undeclared private remote feeds

- **WHEN** a remote that the publication declaration does not name marks itself `forgePrivate`
- **THEN** a push to a declared peer that adds that remote's host refuses under `required` with
  `peer_identity_literal:<form>:<n>:<m>:<line>`
