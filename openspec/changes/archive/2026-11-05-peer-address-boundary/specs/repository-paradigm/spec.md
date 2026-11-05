## ADDED Requirements

### Requirement: Tracked content and commit and tag messages carry no private-class network address

The paradigm SHALL declare one pattern of private-class network addresses: RFC 1918 and RFC 4193 literals, loopback and link-local literals, and names under `.local`, `.internal`, `.lan` or `.home.arpa` in host position. Commit and tag admission SHALL refuse a message that matches it, and ETHOS's content scans SHALL refuse a match in tracked or staged content. No scan SHALL read history, and no gap SHALL repeat the address.

#### Scenario: A commit message names a private forge

- **WHEN** a commit message body carries a remote URL whose host is an RFC 1918 address with a port
- **THEN** commit admission refuses the commit with `commit_message_private_address`
- **AND** the gap does not repeat the address.

#### Scenario: Documentation forms and the public identity pass

- **WHEN** content or a message uses `192.0.2.1`, `2001:db8::1`, `example.invalid` or the public distribution identity `github.com/HengYangDS/<repo>`
- **THEN** the content scans and message admission pass.

#### Scenario: A merge message names only a project path

- **WHEN** a merge message ends with `See merge request <group>/<project>!7` and names no host
- **THEN** commit admission accepts it, because the pattern judges address structure, not names.

#### Scenario: A tag message names a private host

- **WHEN** a signed tag's message names a host under `.internal` with a port
- **THEN** tag admission refuses the tag with `release_tag_message_private_address`.

#### Scenario: Only history holds an address

- **WHEN** a repository's history holds a private-class address and neither its tracked files nor its staged change do
- **THEN** both content scans pass.

#### Scenario: A code attribute shares a private suffix

- **WHEN** content names `threading.local` or `version.local` outside host position
- **THEN** the content scans pass.

#### Scenario: An immutable record is redacted

- **WHEN** a record replaces a private literal with `[redacted:private-network-address:hmac-sha256:<64 lowercase hex>]`
- **THEN** the content scans pass.
