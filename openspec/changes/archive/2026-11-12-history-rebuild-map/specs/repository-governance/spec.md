## MODIFIED Requirements

### Requirement: Attestation lifetimes end with the transition that consumes them

Every Attestation SHALL have exactly one lifetime derived from its predicate and existing bindings:
operation, head, lineage, window or open-predicate. A lifetime SHALL end only on positive evidence
that the set update observes, never on the absence of a branch or ref alone. A rebuild's records
SHALL share the lifetime key `rebuild:<id>` as permanent provenance.

#### Scenario: A Work Lane is retired or its branch is absent

- **WHEN** a lane's retirement effect is selected or its branch is missing
- **THEN** its operation members remain while proof admission can resolve archived intent or
  proposal retirement can resolve refresh provenance through them
- **AND** they end together at the first set update that observes that the lane's branch is absent
  and no commit its ref updates name is reachable from a selected commit or a present pre-repair
  object

#### Scenario: A reader of a retired lane's records cannot be observed

- **WHEN** an update cannot observe whether proof admission or proposal retirement still selects a
  retired lane's records
- **THEN** those records remain and the update reports the gap

#### Scenario: An accepted head is superseded

- **WHEN** closeout advances the accepted ref from one commit to a later one
- **THEN** the proof, integration and publication records of the earlier commit end once no local
  ref, fully peeled tag, worktree HEAD or declared peer's last publication selects it
- **AND** its acceptance record remains as provenance for historical maintenance bases
- **AND** the current head's proof, acceptance and publication records remain

#### Scenario: Maintenance starts from a historical accepted base

- **WHEN** a native maintenance lane selects an earlier accepted base after the current train
  advances
- **THEN** its original accepted-effect record remains selectable and fully validated
- **AND** the new source still requires current proof, signatures, actor and Lease admission
- **AND** retaining provenance does not restore an expired proof or authorize an effect

#### Scenario: A release tag or repair lineage still exists

- **WHEN** a release tag exists, or a governed ref or a declared peer still reaches a pre-repair
  object
- **THEN** its release or repair record remains
- **AND** the record of a kept runtime generation and the starter formation also remain

#### Scenario: A tag or runtime package is no longer observed

- **WHEN** a release tag or a runtime package is missing locally
- **THEN** the release record and every accepted release identity remain
- **AND** a repair record other than a rebuild's ends only once every pre-repair object it names is
  absent locally

#### Scenario: A rebuild's records are permanent

- **WHEN** every pre-repair object that a record under `rebuild:<id>` names is absent locally
- **THEN** that record remains, as DR-0018's historical artifact attestations do
- **AND** no set update ends it

#### Scenario: Lifetime facts cannot be observed

- **WHEN** an update cannot observe refs, worktrees or pre-repair objects
- **THEN** it removes no member and reports the gap

#### Scenario: A validity window passes

- **WHEN** a member's `valid_until` has passed
- **THEN** the next set update removes it

#### Scenario: A predicate has no product reader

- **WHEN** a member's predicate has no product lifetime
- **THEN** the member remains until an admitted release removes it

#### Scenario: A needed member has ended

- **WHEN** a transition requires a member that has left the set
- **THEN** the transition fails closed with its existing missing-evidence gap
- **AND** it does not infer the absent member

### Requirement: Remote publication observations preserve epistemic state

The existing remote-publication effect adapter SHALL be the sole owner of bounded live remote-ref
observation, of exact refs and of namespaces. It SHALL preserve whether a target ref is present,
absent, unavailable, or not observed because an earlier publication precondition failed, and a
failure report SHALL carry no stderr. Public CLI and Git hooks SHALL consume only complete
observations and SHALL NOT recreate availability, ancestry, or object-identity judgments from
missing coordinates.

#### Scenario: exact publication uses the target observer

- **WHEN** `ethos publish --ref <full-ref> --probe-remote` evaluates declared peers
- **THEN** the remote-effect adapter SHALL perform one bounded observation for each exact peer/ref
  target
- **AND** remote-tracking state or general reachability SHALL NOT substitute for that exact ref
  fact.

#### Scenario: publication fails before remote observation

- **WHEN** source trust, source identity, or another pre-observation publication precondition fails
- **THEN** publication SHALL return a structured non-passing result with that exact upstream gap
- **AND** it SHALL NOT index, synthesize, or report a remote object OID.

#### Scenario: a required remote fact is unavailable

- **WHEN** an exact target observation times out, cannot start, or exits without a valid ref result
- **THEN** publication SHALL return verdict `unknown` with the exact peer/ref missing fact, command
  boundary, cwd, and exit or timeout state, and no stderr
- **AND** it SHALL NOT report the ref as absent, divergent, or non-fast-forward.

#### Scenario: a divergent remote ref is observed

- **WHEN** a successful observation returns an existing OID that is neither the desired OID nor an
  admitted fast-forward predecessor
- **THEN** publication SHALL return verdict `block` with the observed OID and target-drift reason
- **AND** no remote mutation SHALL occur.

#### Scenario: apply re-observes the exact request

- **WHEN** a valid publication request is applied
- **THEN** every target SHALL be re-observed through the same bounded observer before the first
  effect and after its peer-local exact CAS
- **AND** unavailable post-observation SHALL not be reported as successful publication.

#### Scenario: A namespace is listed through the same observer

- **WHEN** a rebuild, proposal absorption or the push check lists a peer's namespace or reads its
  advertisement
- **THEN** it reads through the same bounded observer, the review namespaces named as the
  publication retirement owner names them
- **AND** a failed listing reports the peer and its fixed gap, and no stderr

## ADDED Requirements

### Requirement: A Change-local record authorizes one history rebuild

A history rebuild SHALL be authorized only by version 1 of `rebuild.toml` in the authorizing
Change's directory, landed by a normal signed landing. The record SHALL bind only when its blob is
the one at its path in the accepted head `old` and in the rebuilt image, `base..old` touches only
the authorizing Change, and the refs the rebuild moves are the blob's ref set. Its expiry SHALL gate
only a new apply.

#### Scenario: Version 1 of the record is complete

- **WHEN** an adopter lands version 1 of the record
- **THEN** it holds `version`, `id`, `owner`, `reason`, `expires`, `base`, `key` with only its
  `generation`, `[refs]` and `[transform]`
- **AND** every later runtime reads a version 1 record with exactly these fields
- **AND** every later runtime counts occurrences and resolves witnesses for it by version 1's
  occurrence model, discovered forms and pre-images, so the record is not re-landed after a later
  release, and a change to those rules takes a new record version

#### Scenario: The key's generation binds the record

- **WHEN** readiness or the apply reads a key whose generation, as the shared redaction derives it,
  differs from the record's `key.generation` or from the last generation that the repository
  recorded in a redaction or a rebuild attempt
- **THEN** it refuses by a fixed gap before it writes anything, the second as
  `redaction_key_generation_changed`
- **AND** the record names no credential store, and ETHOS reads none

#### Scenario: A rebuild's generation binds a later redaction

- **WHEN** a rebuild attempt has recorded its key's generation and a later redaction reads a key of
  another generation
- **THEN** the redaction refuses `redaction_key_generation_changed` unless it rotates
- **AND** the rebuild writes no redaction record of its own

#### Scenario: The record does not bind

- **WHEN** the record's blob at its path differs between `old` and the rebuilt image, `base..old`
  touches a path outside the authorizing Change, or the refs to move differ from the blob's ref set
- **THEN** readiness and the apply refuse by a fixed gap and write nothing

#### Scenario: The record has expired

- **WHEN** the record's `expires` has passed
- **THEN** a new apply refuses
- **AND** an attempt that an earlier apply recorded still recovers

### Requirement: A rebuild record declares every ref and each peer's state

The record's `[refs]` SHALL declare every local ref outside the allowlist with its disposition, its
local old value and, per peer, its expected state: that value, a declared peer value or `absent`.
The dispositions SHALL be `rebuild` for branches, `retag` for annotated tags, `retire` for any ref
and `keep` for a ref that is not affected. A ref SHALL be affected when any object it reaches, its
own tag object included, holds a declared item or trailer.

#### Scenario: Every ref and each peer's state is declared

- **WHEN** an adopter lands a record for a repository whose peers hold some refs at other values or
  not at all
- **THEN** `[refs]` declares every local ref outside the allowlist with its disposition and local
  old value, and each peer's state as that value, a declared peer value or `absent`
- **AND** dev, main and candidate/dev are declared `at old`, since the record lands in `old` itself

#### Scenario: Allowlisted refs need no declaration

- **WHEN** the repository holds `refs/ethos/attestations-set`, the declared refs' remote-tracking
  refs, a `refs/remotes/<peer>/HEAD` that resolves to one of them, a remote-tracking ref that holds
  a declared peer value, or the record's `rebuilt/` refs
- **THEN** `[refs]` does not declare them, and every other local ref is declared

#### Scenario: A disposition with nothing to rewrite

- **WHEN** a `rebuild` or `retag` ref reaches no affected object
- **THEN** readiness refuses by a fixed gap
- **AND** a `retire` or a `keep` of such a ref is admitted

#### Scenario: A ref is affected through its own tag object

- **WHEN** a tag object's own message holds a declared item or trailer while its target is
  unaffected
- **THEN** the tag is affected, and readiness refuses its `keep` by a fixed gap
- **AND** readiness refuses its `retag` by a fixed gap that names the ref and points to `retire`,
  since a re-tag needs a mapped target

#### Scenario: A ref outside branches and tags can only retire

- **WHEN** the record declares a ref outside `refs/heads/` and `refs/tags/` that the allowlist does
  not cover, such as `refs/notes/*`, `refs/replace/*`, `refs/stash` or `refs/prefetch/*`
- **THEN** readiness admits only `retire` for it, and refuses any other disposition by a fixed gap

#### Scenario: A tag of a tag cannot be re-tagged

- **WHEN** a `retag` ref's tag object targets another tag object
- **THEN** readiness refuses by a fixed gap that names the ref and points to `retire`, since a
  re-tag re-creates one level on the peeled commit

#### Scenario: A lightweight tag can only retire

- **WHEN** the record declares a lightweight tag
- **THEN** only `retire` is admitted for it, since `retag` re-creates annotated tags and ETHOS
  publishes no lightweight tag

### Requirement: Rebuild transform entries declare items by keyed digest

The record's `[transform]` SHALL declare the trailers and exact, owner-confirmed closing message
paragraphs to remove; hosts, paths and ports, each with a witness; typed spans; IDs with contexts
from the shared named set; and `retain` prefixes. Every entry but a `retain` prefix SHALL be a keyed
64-hex digest with its discovered `count`; a `retain` prefix SHALL be clear public text with no
count. The transform SHALL refuse what it cannot replace, rename nothing and keep every identity
header.

#### Scenario: An entry the record cannot hold refuses

- **WHEN** the record holds a free string, a host outside the pattern, a one-segment path, an ID
  without a context or with an unknown or twice-named context, or an entry whose `count` differs
  from the count readiness discovers; a witness is misplaced, its object reached by no declared old
  value or its result's HMAC under the supplied key unequal to its entry's digest; or an original
  already holds a marker
- **THEN** readiness and the apply refuse by a fixed gap that repeats no value, and nothing is
  written

#### Scenario: A witness names one scan result

- **WHEN** a host, path or port entry carries its witness in the landed record blob
- **THEN** the witness `{ object, path, n }` names the `n`-th result, counting from 1, that the
  shared scan attributes to the entry in a commit's or a tag's message, without `path`, or in the
  blob at `path` in a commit's tree
- **AND** no witness names a blob or a tree by its own ID, and the landing commit that lands the
  record blob signs every witness

#### Scenario: The public peer's path bounds declared paths

- **WHEN** a declared path entry's digest equals the `path` image of the public path, or of one of
  its segment-boundary prefixes, of the declared public-distribution peer, or that peer cannot be
  resolved
- **THEN** readiness refuses by a fixed gap

#### Scenario: A host outside the pattern refuses

- **WHEN** a declared host's bytes, placed after `//`, do not match the paradigm's private-address
  pattern, and it is neither a former Go module host tied as an import path's first element nor a
  host that the local peer feed protects
- **THEN** readiness refuses by a fixed gap
- **AND** a former Go module host tied so, or a host that the feed protects, is admitted

#### Scenario: A protected path is tied to its peer

- **WHEN** a declared path of two or more segments, counted after decoding, follows no declared
  host, port or scp colon as a leading prefix and is the full path of no merge-request citation
- **THEN** readiness refuses it as untied by a fixed gap
- **AND** a tied path's lone occurrences elsewhere take its marker

#### Scenario: An ID is replaced only inside its named contexts

- **WHEN** an ID entry is digits only, tied by one `CI_PROJECT_ID=<ID>` occurrence, and names its
  contexts from the shared grammar's named context set, its value a digest
- **THEN** the transform replaces that ID inside those contexts and nowhere else

#### Scenario: Each entry carries its discovered count

- **WHEN** readiness counts the results that the shared scan attributes to each entry over every
  distinct object that the declared old values reach, each object once
- **THEN** it reports each entry's count by the entry's index, never by value, for the owner to
  write as that entry's `count`
- **AND** a later readiness or the apply refuses by a fixed gap when a discovered count differs from
  an entry's `count`

#### Scenario: A retained prefix keeps only public path bytes

- **WHEN** a declared host, port or scp colon is followed by a clear `retain` prefix
- **THEN** the host is still replaced, the prefix's bytes stay, and the rest of the span is still
  scanned
- **AND** only readiness and the apply evaluate the retain set, and no reader needs it
- **AND** the prefix carries no `count`; readiness reports its occurrence total by the prefix's
  index for the owner's review

#### Scenario: A retain prefix that could hide identity refuses

- **WHEN** a `retain` prefix is one segment or `/`, contains a declared item, matches the
  private-address pattern, or never follows a declared item
- **THEN** readiness refuses by a fixed gap

#### Scenario: A declared item in a header or a tree entry name refuses

- **WHEN** any commit or tag header, `author`, `committer`, `tagger` and `mergetag` included, or a
  tree entry name of an object that a declared ref reaches holds a declared item
- **THEN** readiness refuses by a fixed gap, since the transform rewrites no header and renames
  nothing

#### Scenario: Declared message items leave the message

- **WHEN** a commit message carries a declared trailer or ends with a declared closing paragraph
- **THEN** the rebuilt message drops that trailer or paragraph, and no undeclared byte of it changes

#### Scenario: One Go string gets one replacement

- **WHEN** a declared item occurs in identical Go strings across the files of one commit
- **THEN** each identical string gets the same one replacement, so module files, imports and link
  flags agree

#### Scenario: A file the transform cannot keep refuses

- **WHEN** a binary blob holds a declared item, or a reparsed TOML, YAML or JSON file would have
  other keys or value types than its original
- **THEN** the rebuild refuses by a fixed gap before any ref moves

#### Scenario: Followed digests move with their file

- **WHEN** a rebuilt blob holds the SHA-256 of a file whose bytes the transform changed
- **THEN** the transform rewrites that digest to the changed file's SHA-256, round after round until
  none moves, through the shared redaction's digest following

#### Scenario: A quoted original ID is mapped to its image

- **WHEN** a commit message, a tag message or a blob holds a hex token of 7 to 40 characters,
  bounded by non-hex characters, that prefixes exactly one rewritten commit's or tag's ID
- **THEN** the transform replaces it with the rebuilt object's ID at the same length
- **AND** a 64-character token is followed as a content digest, and no original ID survives in the
  rebuilt history, signed or not

#### Scenario: An ambiguous or early quote refuses

- **WHEN** a quoted token prefixes two or more rewritten objects, or the apply reaches a quote of an
  object that the topological order has not rewritten yet
- **THEN** readiness refuses the first, and the apply the second, by a fixed gap

#### Scenario: An item remains at old only under an immutable root

- **WHEN** the tree at `old` holds a declared item outside an immutable root
- **THEN** readiness refuses by a fixed gap

### Requirement: Rebuild counts and witnesses share one occurrence model

A rebuild's counts and witnesses SHALL both count the results of the shared grammar's one scan over
commit messages, annotated tag messages and blob contents, each result attributed to exactly one
entry, the longest declared entry at its position. Every digest SHALL be the keyed HMAC-SHA-256 of
its kind's domain-separated pre-image, which the shared grammar defines as data.

#### Scenario: A span wins over its parts

- **WHEN** a declared span and its own host, port and path entries all match at one position
- **THEN** the scan attributes that result to the span alone

#### Scenario: Counts and witnesses agree across commit shapes

- **WHEN** declared items occur in a merge commit's tree, in a root commit's tree and under a
  renamed path
- **THEN** each entry's count counts every distinct object once, and every witness resolves to a
  result that its entry's count includes

#### Scenario: An item in a tag message is witnessed by the tag

- **WHEN** a declared item occurs only in an annotated tag's message
- **THEN** a witness names that tag without a path, and the item can be declared

#### Scenario: Each kind keys its own pre-image

- **WHEN** span, host, path, port, ID, trailer and paragraph entries and an original's name are
  keyed
- **THEN** span, host and path digests use the shared marker images, and each other kind hashes its
  own `ethos.rebuild.v1` image, so equal bytes of two kinds never share a digest

#### Scenario: A gitlink has no bytes to scan

- **WHEN** a tree that a declared ref reaches holds a gitlink
- **THEN** the scan reads no bytes for it, and it counts toward no entry

### Requirement: A rebuild record names an original in clear only when it is signed

A witness object, a `[refs]` old value, a declared peer value and `base` SHALL be named by ID only
when that commit or tag carries a signature that today's trust anchor verifies. The record SHALL
otherwise name it by the keyed digest of its ID, which readiness and the apply resolve with the key,
and the apply SHALL record its clear ID only in its signed local attempt record, which is never
published.

#### Scenario: An unsigned original is named by keyed digest

- **WHEN** an original that the record names carries no signature that today's trust anchor
  verifies, whatever policy held when it was made
- **THEN** the record names it by the HMAC of `ethos.rebuild.v1\0oid\0` and its ID under the
  record's key, and readiness and the apply find it among the reachable objects
- **AND** the apply records its clear ID in its signed local attempt record, and no publication
  sends that record

#### Scenario: A clear ID of an unsigned original refuses

- **WHEN** the record names by clear ID an original that carries no signature that today's trust
  anchor verifies
- **THEN** readiness refuses by a fixed gap that repeats no value

#### Scenario: A keyless reader resolves through the attempt record

- **WHEN** a keyless reader needs an original that the record names by keyed digest
- **THEN** it reads the clear ID from the signed local attempt record, never from the key

### Requirement: Rebuild readiness proves discovered completeness before any effect

Rebuild readiness SHALL walk the originals of every declared ref once, check main against dev and
every per-peer state, compute the rebuilt image in memory, write nothing and report only by count
and fixed gap name. It SHALL refuse every discovered span or local feed value that the record
neither declares nor retains, every undeclared local ref or declared ref in another state, and every
`retag` or `keep` ref that could not publish afterwards.

#### Scenario: Readiness writes nothing and names no value

- **WHEN** rebuild readiness runs with a record and the key
- **THEN** it walks the originals of every declared ref once and computes the rebuilt image in
  memory
- **AND** it writes no object, ref, record, observation or side repository, and its report holds no
  declared item

#### Scenario: A discovered span that no entry covers refuses

- **WHEN** the walk discovers, in a blob or a message, a host with or without a scheme and port, a
  path after a host or an scp colon, a module path's first element, an encoded path, a merge-request
  citation with its `!<n>`, or an ID-context hit, and the record neither declares nor retains it
- **THEN** readiness refuses by a fixed gap and count

#### Scenario: History that the walk cannot see refuses

- **WHEN** the repository is shallow, holds `info/grafts`, or has a linked worktree whose HEAD is
  detached or that holds a per-worktree ref
- **THEN** readiness refuses by a fixed gap, since the main worktree's ref listing does not show
  that history
- **AND** replace refs change nothing, since ETHOS reads objects with replacement disabled

#### Scenario: Quoted original IDs are counted

- **WHEN** a message or a blob that a declared old value reaches quotes the ID of a rewritten commit
  or tag
- **THEN** readiness counts the quoted IDs per object by kind, never by value

#### Scenario: A feed value that no entry covers refuses

- **WHEN** an object that a declared old value reaches holds a value of the local peer feed, current
  or former, that no entry declares or retains
- **THEN** readiness refuses by a fixed gap, as the push check would refuse that value at
  publication

#### Scenario: Refs must match the record

- **WHEN** a local ref outside the allowlist is undeclared, a declared ref is in another state, main
  differs from dev, a peer's state differs from the declared one, or an affected ref is declared
  `keep`
- **THEN** readiness refuses by a fixed gap

#### Scenario: A ref that could not publish refuses before anything is deleted

- **WHEN** a `retag` ref has neither a valid `release.promote` record nor a mapped maintenance base,
  its transformed tag message names a private address, its original qualification cannot be
  verified, or a `keep` ref is one that ETHOS cannot publish
- **THEN** readiness refuses by a fixed gap
- **AND** it judges a `retag` ref's release-tag policy as the verified image of its original
  qualification, never under today's CHANGELOG grammar

### Requirement: A rebuild reads its peers through one namespace listing

ETHOS SHALL read a rebuild's peers through the remote-publication observer's bounded namespace
listing, covering `refs/heads/`, `refs/tags/` and `refs/ethos/`, and, for counting, the review
namespaces that the publication retirement owner names. For a rebuild the listing SHALL refuse an
undeclared peer ref under `refs/heads/` or `refs/tags/` and any peer ref under `refs/ethos/`; it
SHALL return states and record nothing.

#### Scenario: An undeclared peer ref refuses

- **WHEN** a peer holds an undeclared ref under `refs/heads/` or `refs/tags/`, or any ref under
  `refs/ethos/`
- **THEN** readiness and the apply refuse by a fixed gap

#### Scenario: The listing returns states only

- **WHEN** the listing finds a declared retired tag absent on a peer
- **THEN** it returns that state to its caller and records nothing itself

#### Scenario: A failed peer read carries no stderr

- **WHEN** listing a peer times out or fails
- **THEN** the report names the peer and the fixed gap and carries no stderr

#### Scenario: Peer review refs are counted

- **WHEN** a peer holds review refs, `refs/pull/<n>/head` or `refs/merge-requests/<n>/head`, that
  reach affected commits
- **THEN** readiness counts those whose objects are present locally and reports the rest as unknown

### Requirement: Keyless readiness counts identity without a record

As the census operation of the `lane repair-signature` catalog entry, read-only and taking no record
and no key, rebuild readiness SHALL read the local refs' history with the local feed, the shared
peer identity grammar and the trailer rule, as the keyless redaction preview reads the feed, and
SHALL report only counts by form and ref class.

#### Scenario: Keyless readiness counts without a record

- **WHEN** `ethos lane repair-signature --census` runs
- **THEN** it reports the trailers and identity forms it finds as counts by form and ref class
- **AND** it names no value and writes nothing

### Requirement: Rebuild reports carry no identity

No output, record, plan, cache file, next action or failure report of a rebuild SHALL hold a
declared item. Its failure reports SHALL drop stdout and stderr, and no Git argument it runs SHALL
carry a literal.

#### Scenario: Reports and arguments hold no value

- **WHEN** readiness, the apply, a re-tag, a rollback or `--release` reports, records, caches, plans
  a next action or fails
- **THEN** none of them holds a declared item, a failure report holds no stdout or stderr, and no
  Git argument it ran carried a literal
