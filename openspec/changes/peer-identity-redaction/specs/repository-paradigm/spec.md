## MODIFIED Requirements

### Requirement: Tracked content and commit and tag messages carry no private-class network address

The paradigm SHALL declare one pattern of private-class network addresses: RFC 1918 and RFC 4193
literals, and names under `.local`, `.internal`, `.lan` or `.home.arpa` in host position. Commit and
tag admission SHALL refuse a message that matches it, and ETHOS's content scans SHALL refuse a match
in tracked or staged content. No scan SHALL read history, and no gap SHALL repeat the address.

#### Scenario: A commit message names a private forge

- **WHEN** a commit message body carries a remote URL whose host is an RFC 1918 address with a port
- **THEN** commit admission refuses the commit with `commit_message_private_address`
- **AND** the gap does not repeat the address.

#### Scenario: Documentation forms and the public identity pass

- **WHEN** content or a message uses `192.0.2.1`, `2001:db8::1`, `example.invalid` or the public
  distribution identity `github.com/HengYangDS/<repo>`
- **THEN** the content scans and message admission pass.

#### Scenario: A merge message names only a project path

- **WHEN** a merge message ends with `See merge request <group>/<project>!7` and names no host
- **THEN** commit admission accepts it, because the pattern judges address structure, not names.

#### Scenario: A tag message names a private host

- **WHEN** a signed tag's message names a host under `.internal` with a port
- **THEN** tag admission refuses the tag with `release_tag_message_private_address`.

#### Scenario: Only history holds an address

- **WHEN** a repository's history holds a private-class address and neither its tracked files nor
  its staged change do
- **THEN** both content scans pass.

#### Scenario: A code attribute shares a private suffix

- **WHEN** content names `threading.local` or `version.local` outside host position
- **THEN** the content scans pass.

#### Scenario: An immutable record is redacted

- **WHEN** a record replaces a private literal with a peer marker
  `<32 lowercase hex>.<32 lowercase hex>.private-peer.invalid`
- **THEN** the content scans pass.

#### Scenario: Loopback and link-local literals pass

- **WHEN** content or a message names a loopback or link-local literal, such as a port bound to the
  loopback interface
- **THEN** the content scans and message admission pass, because such a literal discloses no peer

## ADDED Requirements

### Requirement: Peer identity markers are keyed, canonical and shared

ETHOS SHALL define one grammar for protected peer identity: the occurrence kinds `url`, `scp`,
`authority` and bare `host`; the marker `<hex32>.<hex32>.private-peer.invalid`, one HMAC-SHA-256 of
a NUL-joined pre-image of version, kind, host, port and path that never hashes scheme or userinfo;
and keyed replacement of project IDs and ports in closed contexts. Every reader of markers SHALL use
this grammar.

#### Scenario: A URL becomes one marker

- **WHEN** a fed host with a port and a namespace path appears after `//` with userinfo
- **THEN** the host, port and whole leading segments become one marker
- **AND** the scheme, the userinfo and the rest of the line stay byte-identical

#### Scenario: An scp form keeps its colon

- **WHEN** a fed host appears as `git@<H1>:<F1>`
- **THEN** it becomes `git@<marker>:<marker>`, the path a standalone `path` marker
- **AND** the `scp` and `url` markers of the same parts differ

#### Scenario: A key that cannot key refuses

- **WHEN** the key is not 64 lowercase hex characters with at most one trailing newline, or is all
  zero
- **THEN** the reader refuses with `redaction_key_invalid` and nothing is written

#### Scenario: A number in a closed context is replaced

- **WHEN** a fed project ID or port appears in a closed context
- **THEN** it is replaced by a keyed number in its range that differs from the original, every other
  replacement and every fed value and is absent from the domain
- **AND** more than 4,096 probes refuses with `numeric_replacement_exhausted`
