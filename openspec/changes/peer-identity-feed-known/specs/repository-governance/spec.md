## MODIFIED Requirements

### Requirement: A push refuses the protected peer identity it adds

Under `peer_identity.mode = "required"`, read at the commit that push admission trusts, push
admission SHALL read the commits a push adds beyond every tip its peer advertises and a pushed tag's
message, and SHALL refuse a fed host, a fed full path, a port after any host and a closed context
with a fed value of any protected peer, as `peer_identity_literal:<form>:<n>:<m>:<line>`. Before
it reads the advertisement, it SHALL refuse a feed the clone cannot know: an invalid publication
declaration with its own required gaps, else each declared peer whose remote holds no URL in its
`url` or `pushurl` keys as `peer_identity_feed_unreadable:<remote>`, else a feed of nothing as
`peer_identity_feed_empty`. A remote that marks itself `forgePrivate` SHALL feed whether or not
the publication declaration names it. A deletion SHALL pass before the mode is read. No gap
SHALL carry a value, and no history beyond the advertisement SHALL be read.

#### Scenario: A push adds a fed literal

- **WHEN** a commit or its message names a protected peer's host and the peer does not yet hold it
- **THEN** push admission refuses with `peer_identity_literal:<form>:<n>:<m>:<line>`
- **AND** the same content passes once the peer advertises it

#### Scenario: The advertisement cannot be read

- **WHEN** the peer's advertisement cannot be read under `required`
- **THEN** push admission refuses with `peer_identity_range_unknown:<remote>`

#### Scenario: The mode is disabled or unread

- **WHEN** the trusted commit's profile declares `disabled`, or its profile cannot be read
- **THEN** push admission reads nothing, and an unread mode is the advisory
  `peer_identity_mode_unread`

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
