## MODIFIED Requirements

### Requirement: Commit policy applies to exact introduced commit ranges

ETHOS SHALL compile the commit policy, the paradigm's subject grammar and SSH signature with the
optional tracked `.ethos/workspace.toml [commit_policy]` declaration, through the existing
repository-policy owner and apply that compiled policy only to the commits newly introduced by one
proposed Git ref update. The range projection SHALL be provider-neutral, SHALL preserve the
repository object format, and SHALL NOT reinterpret or revalidate commits already reachable from the
trusted baseline.

#### Scenario: Existing ref receives a normal fast-forward

- **WHEN** a non-delete update supplies readable remote and proposed commit objects
- **THEN** ETHOS validates each commit reachable from the proposed commit but not from the remote
  commit in deterministic oldest-first order
- **AND** commits already reachable from the remote commit are not revalidated.

#### Scenario: Existing ref receives a non-fast-forward update

- **WHEN** the proposed commit does not descend from the readable remote commit
- **THEN** ETHOS still reports and validates exactly the commits newly reachable from the proposed
  commit
- **AND** the existing topology and ref-movement policy independently decides whether the
  non-fast-forward effect is admissible.

#### Scenario: A new proposal ref has a trusted accepted baseline

- **WHEN** the remote object ID is the repository-native zero object ID and the target has proposal
  role
- **THEN** ETHOS resolves the declared remote's accepted ref as the trusted baseline and validates
  only the proposed commits not reachable from it
- **AND** it blocks if that baseline is absent, unreadable, or not an ancestor of the proposed
  commit.

#### Scenario: A new non-proposal ref has no trustworthy baseline

- **WHEN** the remote object ID is zero and no exact trusted baseline is supplied or derivable for
  the target
- **THEN** ETHOS fails closed with a baseline gap
- **AND** it does not substitute the root commit or scan all repository history.

#### Scenario: An accepted or release object is projected to an absent ref

- **WHEN** an accepted branch, release branch, or annotated release tag has a zero remote object ID
- **AND** the exact proposed commit has one valid accepted-closeout Attestation
- **THEN** ETHOS uses that Attestation's accepted pre-state as the trusted historical baseline
- **AND** local publication dry-run and the real pre-push transport validate the same introduced
  revisions without trusting another remote or an unrelated sibling ref.

#### Scenario: A delete update is observed

- **WHEN** the proposed object ID is the repository-native zero object ID
- **THEN** commit-range admission reports a no-range delete result
- **AND** it leaves deletion authority to the existing ref policy.

#### Scenario: An annotated tag is proposed

- **WHEN** either endpoint names an annotated tag object
- **THEN** range admission peels that endpoint to its exact commit before deriving introduced
  commits
- **AND** tag-object trust remains governed by the existing publication owner.

#### Scenario: Commit policy is absent or malformed at the proposed tip

- **WHEN** the proposed committed tree contains no `[commit_policy]` table
- **THEN** ETHOS applies the paradigm's subject grammar and SSH signature to the introduced range
- **AND** when the table is present but malformed, admission fails closed before returning a passing
  range result.

#### Scenario: A rebuilt branch is pushed

- **WHEN** a rebuilt branch is pushed to a peer in any state, an empty one included
- **THEN** the trusted baseline is the verified image of the branch's declared local old value, not
  an accepted-closeout pre-state
- **AND** commits at or below that image, the verified image of accepted history, are not
  revalidated, and each commit beyond it is validated as in any push

#### Scenario: A re-created tag is pushed before any branch reaches it

- **WHEN** a re-created tag is pushed to a peer where no published branch reaches its target, an
  empty peer included
- **THEN** the trusted baseline is the verified image of the original tag's target
- **AND** nothing at or below that image is revalidated, and the tag publishes on its original
  qualification

### Requirement: Bounded accepted signature replacement

ETHOS SHALL admit replacement only from the current accepted policy, explicit authorization, an
exact unsigned source, a trusted signed replacement, selected ref coordinates and clean linked
worktrees; a rebuild SHALL instead be admitted from its bound record and SHALL move each declared
ref to its own value. Each effect SHALL recheck its own preconditions. Existing effect evidence
SHALL support recovery without becoming reusable authorization.

#### Scenario: Select only required local refs

- **WHEN** current policy identifies the accepted ref and coupled local projections
- **THEN** the plan binds every selected ref to its observed old and desired OID
- **AND** independent release, topic and remote refs remain unchanged
- **AND** an unrelated candidate OID is neither overwritten nor silently included

#### Scenario: Trust and payload are independent conditions

- **WHEN** a replacement has a trusted signature but different preserved bytes
- **THEN** repair rejects it
- **AND** an equal payload with an untrusted signature is also rejected

#### Scenario: Drift blocks the next effect

- **WHEN** a bound ref, policy, trust input, index or linked worktree has changed
- **THEN** the next affected mutation is rejected with the precise coordinate
- **AND** already observed effects remain accurately reported

#### Scenario: Partial worktree synchronization recovers safely

- **WHEN** selected refs moved but one linked worktree could not synchronize
- **THEN** the result identifies completed and remaining effects
- **AND** recovery re-observes refs and worktrees before continuing
- **AND** unrelated content and refs remain unchanged

#### Scenario: A rebuild moves each declared ref to its own value

- **WHEN** a rebuild applies and its rebuilt objects hold no declared or discovered identity
- **THEN** one ref transaction moves every `rebuild` ref from its declared old value to its own
  rebuilt value, removes every `retire` ref, and holds each `retag` ref's rebuilt target under
  `refs/ethos/rebuild/<id>/rebuilt/`
- **AND** `refs/ethos/attestations-set` is not rewritten

#### Scenario: The rebuild apply refuses an unready repository

- **WHEN** a peer's state differs from the one the record declares, a local ref exists outside the
  declared refs and the record's allowlist, a `work/` or `proposal/` ref exists, a declared worktree
  is dirty, main differs from dev, or the backup bundle lacks a declared old value or a
  release-named commit, or its restore fails `fsck` for one of them
- **THEN** the apply refuses by name before it writes any record, side repository or object

#### Scenario: A declared peer value is held locally

- **WHEN** the record declares a peer value that differs from the local old value
- **THEN** that value is fetched natively with an exact refspec under the peer's remote-tracking ref
  before the bundle is cut, so the bundle and the side repository carry it
- **AND** that remote-tracking ref is admitted exactly when the record declares that peer value

#### Scenario: The hook admits only a rebuild's recorded moves

- **WHEN** a ref under `refs/ethos/rebuild/` moves outside a plan that the rebuild recorded
- **THEN** the reference-transaction hook refuses the move
- **AND** a rollback's moves are admitted inside its one recorded `commit.identity-replace` intent

#### Scenario: An interrupted rebuild recovers

- **WHEN** a rebuild apply stopped after it wrote and signed some rebuilt objects
- **THEN** recovery reuses those signed payloads in topological order instead of signing again

### Requirement: Publication composes historical repair with forward integration

ETHOS SHALL recognize an original peer object through an unambiguous chain of completed native
history repairs and verified rebuilds, each repair conserving exact payloads, ordered parents and
trusted signatures under its recorded source policy. Only refs named throughout the chain SHALL
inherit repaired publication provenance. The peer's advertised object SHALL remain the CAS
precondition, and the last verified replacement tip SHALL own forward commit-range validation.

#### Scenario: Repaired provenance does not substitute for current admission

- **WHEN** a ref inherits repaired publication provenance
- **THEN** current proof, accepted effect, candidate equality and protected publication admission
  are still each required independently

#### Scenario: Signed forward commits follow a verified replacement

- **WHEN** the peer ref holds the recorded repair source and proposed accepted descends from its
  verified replacement
- **THEN** publication recognizes the historical segment as repaired
- **AND THEN** the common range owner checks replacement-to-proposed commits without scanning the
  repaired historical segment as new integration.

#### Scenario: Peer holds an earlier mapped original commit

- **WHEN** the protected peer ref holds an exact original commit in the completed repair mapping and
  the repair replaced that same local ref
- **THEN** pre-push and publication readiness use the verified replacement tip as the
  forward-validation baseline
- **AND THEN** the peer's advertised old OID remains the exact CAS precondition rather than being
  substituted with the mapped or replacement OID.

#### Scenario: A forward commit violates policy

- **WHEN** a descendant after the verified replacement has an invalid subject, identity or required
  signature
- **THEN** range admission rejects that descendant despite valid repair provenance.

#### Scenario: Repair provenance does not establish the requested relationship

- **WHEN** the target ref is not in the repair, the peer's old OID is not a mapping key, replacement
  ancestry is absent, or repair evidence is missing, invalid or ambiguous
- **THEN** the request is not admitted as a repaired-history publication
- **AND THEN** no remote or local ref is changed by the observation.

#### Scenario: Accepted publication consumes the verified forward baseline

- **WHEN** public pre-push or publication evaluates accepted descendants after a verified repair of
  the peer's exact old object or mapped historical prefix
- **THEN** the accepted topology check evaluates forward ancestry from the verified replacement
  while still requiring the current candidate head
- **AND THEN** proposed-object proof and its accepted effect remain required
- **AND THEN** each peer applies only its observed old-to-proposed ref transaction.

#### Scenario: Repaired ancestry cannot excuse missing current acceptance

- **WHEN** the repair relation is valid but current proof, accepted effect or candidate equality is
  absent
- **THEN** publication is rejected without changing either peer.

#### Scenario: An original prefix survives a subsequent repair

- **WHEN** a verified replacement enters a later repair's exact source history and that completed
  repair replaces its object before current forward work
- **THEN** original-object provenance composes both native mappings
- **AND THEN** commit-range admission checks only last-tip descendants, retaining every repair
  witness and the peer's original CAS object
- **AND THEN** an invalid forward subject or signature still rejects publication.

#### Scenario: A predecessor or ref relationship is absent

- **WHEN** any necessary completed repair is missing or invalid, multiple paths establish the
  relation, or a ref is absent from a necessary repair effect
- **THEN** that repaired-history relationship is not admitted
- **AND THEN** no local or remote ref changes during observation.

#### Scenario: A verified rebuild joins the chain

- **WHEN** a ref's original reaches its image through a verified rebuild, alone or after completed
  repairs, and the rebuild's record declares that ref
- **THEN** publication recognizes the original through that chain, reading the rebuild edge through
  its verification owner
- **AND THEN** a ref that the record does not declare inherits no repaired publication provenance.

### Requirement: Attestation lifetimes end with the transition that consumes them

Every Attestation SHALL have exactly one lifetime derived from its predicate and existing bindings:
operation, head, lineage, window or open-predicate. A lifetime SHALL end only on positive evidence
that the set update observes, never on the absence of a branch or ref alone. A rebuild's records
SHALL share the lifetime key `rebuild:<id>` as permanent provenance, and a retired tag's first
observed absence on a re-created peer SHALL be that peer's latest state for it.

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

- **WHEN** the owner expires the reflog, runs `gc --prune=now` or deletes the side repository after
  a rebuild's apply
- **THEN** its attempt, result, applied ref-update, observed-absence and `--release` records under
  `rebuild:<id>` remain, as DR-0018's historical artifact attestations do
- **AND** no set update ends one of them, and `ethos hook retire-records` plans no rebuild kind

#### Scenario: A command with write authority records the first absence

- **WHEN** `ethos publish` applies to a re-created peer, or `--release` runs before it requires the
  absences, and the peer reader finds a declared retired tag absent there
- **THEN** that command records the first such observation under `rebuild:<id>`
- **AND** rebuild readiness, which is read-only, records none

#### Scenario: An observed absence is the peer's latest state

- **WHEN** ETHOS has recorded the first observation that a retired tag is absent on a re-created
  peer
- **THEN** the set update takes that observation, by its issue time, as that peer's latest state for
  that ref
- **AND** after a tag retires, both peers are re-created and published, the reflog expires and
  `gc --prune=now` runs, a set update still ends members

#### Scenario: An absence is not yet observed

- **WHEN** the owner's gc runs before the first observation that a retired tag is absent on a
  re-created peer
- **THEN** lifetime observation of that ref stays unknown until that observation is recorded
- **AND** the set update treats that ref's state as a lifetime fact it cannot observe

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

### Requirement: Accepted history repair preserves original acceptance provenance

Accepted-source consumers SHALL resolve original acceptance through validated completed
history-repair relations for the exact accepted ref; across a verified rebuild they SHALL resolve it
by looking the rebuilt image up in the record's mapping. They SHALL retain the original Attestation
and distinguish its coordinates from current source coordinates. Equal trees alone SHALL NOT
establish acceptance or authority.

#### Scenario: A repaired accepted source is proved and released

- **WHEN** governed history repair replaces an accepted commit and a new exact-source proof succeeds
- **THEN** closeout and release retain the original accepted-effect Attestation
- **AND** validated repair relations explain the current source coordinates
- **AND** current actor-owned Lease admission is independent of the proof's original execution root

#### Scenario: Related bytes do not prove current authority

- **WHEN** repair provenance is absent, ambiguous, cyclic or does not select the accepted ref
- **THEN** acceptance is not inferred from matching trees or a historical identity
- **AND** unrelated plans are not decoded as potential authority for that source

#### Scenario: Ordinary publication does not validate rewritten history

- **WHEN** a peer ref is already current, absent or an ancestor of the signed source
- **THEN** exact publication admission uses that observed relation without validating a historical
  repair
- **AND** a divergent peer still requires completed repair provenance or is rejected

#### Scenario: A rebuilt accepted source keeps its original acceptance

- **WHEN** a verified rebuild maps an accepted commit to its image and a new exact-source proof of
  the image succeeds
- **THEN** release and publication find the image's original through the record's mapping and retain
  the original accepted-effect Attestation
- **AND** with the originals absent, acceptance is not inferred from the image

### Requirement: A repaired release tag is re-created on its replacement commit

ETHOS SHALL re-create a release tag whose target a completed signature repair or a verified rebuild
replaced as a signed annotated tag on the mapped commit, keeping the original name, tagger, date and
message, except that a rebuild's transform prepares the message, and SHALL record one attestation
binding both tag objects, the mapping attestation and the mapped target. An unmapped target, a
missing original, an occupied name or an untrusted signer SHALL refuse by name.

#### Scenario: A repaired tag is re-created

- **WHEN** a release tag targets a commit that a completed signature repair mapped to a replacement
- **THEN** the re-created tag targets the replacement with the original header and message
- **AND** one attestation binds the old and new tag objects, the mapping attestation and the target

#### Scenario: A batch holds an unmapped tag

- **WHEN** a re-tag batch names a tag whose target no completed repair mapped
- **THEN** that tag refuses by name and no ref moves

#### Scenario: A rebuilt tag is re-created with its prepared message

- **WHEN** `ethos land --retag` re-creates a `retag` ref whose rebuilt target the rebuild holds
  under `refs/ethos/rebuild/<id>/rebuilt/`
- **THEN** it reads, through the record-resolution owner and without the key, the transformed
  message that the rebuild's signed result record carries
- **AND** the re-created tag targets that commit with the original name, tagger and date and that
  message, and `land --retag` applies its release-tag policy to it
- **AND** the prepared message carries no signature armor of any format that ETHOS knows: SSH,
  OpenPGP or X.509

#### Scenario: Re-tag reads its original after the owner's gc

- **WHEN** the owner has expired the reflog and run `gc --prune=now` after a rebuild
- **THEN** a re-tag preview and apply read the original tag through the side repository without a
  backup bundle
- **AND** the process that reads the original writes nothing, and the replacement is written by a
  process without the side repository attached

### Requirement: A re-created release tag publishes on its original qualification

Publication SHALL qualify a re-created release tag by the proof that its original tag's release
record embeds, admitted as recorded on the original commit, only when one re-tag receipt binds the
exact tag object and its mapping still verifies; the original proof's set member SHALL NOT be
required. Across a rebuild, the tag's original qualification, verified through the bijection, SHALL
qualify its image. A re-created tag without a receipt SHALL keep the current policy.

#### Scenario: A re-created tag under a later policy

- **WHEN** a re-created tag is published after the policy changed and the original proof's set
  member has ended
- **THEN** publication admits the original release record's proof and the peer receives the
  re-created tag

#### Scenario: A re-created tag without its receipt

- **WHEN** no re-tag receipt binds the re-created tag object
- **THEN** its publication is judged under the current policy, and without a current proof it
  refuses before any peer changes

#### Scenario: A rebuilt tag on an older commit publishes

- **WHEN** a rebuild re-created a release tag whose target is an older commit
- **THEN** publication admits it on its original release record's proof, also after the owner ran
  `gc --prune=now`

#### Scenario: A maintenance release publishes on its verified image

- **WHEN** a rebuild re-created a maintenance release tag whose release range archives a Change
  whose original held a declared span
- **THEN** verification proves the bijection between the original range and the mapped range, and
  release provenance admits the mapped range as the original range's verified image
- **AND** neither release provenance nor push admission of the maintenance closeout re-judges the
  rebuilt commits under the current commit policy or the keyless peer identity verifier, and the tag
  publishes

#### Scenario: An older CHANGELOG grammar keeps its qualification

- **WHEN** a rebuilt release tag's CHANGELOG uses a grammar older than today's
- **THEN** readiness and publication judge its release-tag policy as the verified image of its
  original qualification, and the tag publishes

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

#### Scenario: A refused push is classified without its stderr

- **WHEN** a peer refuses a push
- **THEN** the publication owner reads the push's stderr only to match it against a fixed set of
  forge patterns that it holds as data, and a size refusal emits `publication_pack_refused:<peer>`
  with the plan's recorded step sizes
- **AND** an unmatched failure keeps its fixed failure gap, and neither result carries a byte of the
  stderr

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

### Requirement: A rebuilt history holds no declared or discovered identity

Before any ref moves, the apply SHALL prove that nothing reachable from a rebuilt branch, a tag-only
target or a kept ref, and no `retag` target's transformed message, holds a declared item, a
discovered span that no entry declares or retains, or a match of the paradigm's private-class
address pattern, and that every rebuilt ref is connected in the main object store alone.
`land --retag` SHALL prove the same for each re-created tag when it creates it.

#### Scenario: Rebuilt objects are proved before any ref moves

- **WHEN** the apply has written and signed the rebuilt objects and transformed each `retag`
  target's message
- **THEN** it proves the property over everything reachable from each rebuilt branch, tag-only
  target and kept ref and over each transformed message, and that each rebuilt ref is connected
  without the side repository
- **AND** when either proof fails, no ref moves
- **AND** the signed result record then carries each `retag` target's transformed message

#### Scenario: A re-created tag is proved when it is created

- **WHEN** `ethos land --retag` would create a tag whose object, message or target reaches a
  declared item, a discovered span that no entry declares or retains, or a private-address match
- **THEN** it refuses before the tag ref moves

### Requirement: Rebuild reports carry no identity

No output, record, plan, cache file, next action or failure report of a rebuild SHALL hold a
declared item. Its failure reports SHALL drop stdout and stderr, and no Git argument it runs SHALL
carry a literal.

#### Scenario: Reports and arguments hold no value

- **WHEN** readiness, the apply, a re-tag, a rollback or `--release` reports, records, caches, plans
  a next action or fails
- **THEN** none of them holds a declared item, a failure report holds no stdout or stderr, and no
  Git argument it ran carried a literal

### Requirement: Rebuild originals live in an owner-only side repository

After the key verifies against every witness, the apply SHALL create
`<common>/ethos/rebuild/<id>/originals.git`: owner-only, with `gc.auto=0`, no hooks, no remote and
no alternates either way, holding each declared old value under its own ref. Readers SHALL attach it
per read-only Git process, and a process that attaches it SHALL write nothing. It SHALL end only on
a recorded `--release` plus the owner's decision to delete it.

#### Scenario: A wrong key leaves no side repository

- **WHEN** the key does not verify against every witness
- **THEN** the apply refuses before any rebuild record or side repository exists

#### Scenario: The side repository holds the verified originals

- **WHEN** the apply creates the side repository
- **THEN** it builds it from the restore that verified the backup bundle
- **AND** every declared old value stays reachable from its own ref there after the owner's
  `gc --prune=now` in the main repository or a `gc` in the side repository

#### Scenario: An attached process writes nothing

- **WHEN** a reader or a hook needs an original
- **THEN** it attaches the side repository as an alternate object directory of that one read-only
  Git process, a hook in its own process, and that process writes nothing

#### Scenario: A gained alternates file refuses

- **WHEN** the side repository has gained an `objects/info/alternates` file
- **THEN** every reader refuses by a fixed gap

#### Scenario: The side repository ends with the owner's decision

- **WHEN** `--release` is recorded and the owner deletes the side repository
- **THEN** a reader that asks for a rebuild edge answers `unknown` by a fixed gap
- **AND** the rebuilt commits remain ordinary signed history for every other reader

### Requirement: Readers verify a rebuild through one owner without the key

One record-resolution owner SHALL hold a rebuild's per-ref results, union mapping, inverse lookup by
mapped image and each `retag` target's prepared message; one verification owner SHALL verify a
completed rebuild without the key, from the record blob binding, the signed attempt and result
records, the structural bijection and the keyless private-address scan. Every reader SHALL read a
rebuild only through them, answering `unknown` for a rebuild edge without the originals.

#### Scenario: Verification recomputes no transform

- **WHEN** a reader verifies a completed rebuild
- **THEN** it checks the record blob binding, the signed attempt and result records whose witness
  check bound the key, the structural bijection, in which parents, dates, authors and committers are
  byte-equal and only the objects that the result names differ, and the keyless private-address scan
- **AND** it recomputes no transform, which needs the key and is readiness's job

#### Scenario: Every reader reads through the owners

- **WHEN** the reference-transaction hook, historical-source admission, re-tag, release,
  publication, conservation, archive provenance, the attested archive transition or marker pairing
  reads across a rebuild edge
- **THEN** it resolves the edge through the one record-resolution owner and verifies it through the
  one verification owner, without a key

#### Scenario: Readers pass after the owner's gc

- **WHEN** the owner has run `reflog expire --expire=now --all` and `gc --prune=now` after a rebuild
- **THEN** verification, a re-tag preview, a re-tag apply, a publication and replayed hook admission
  pass through the side repository

#### Scenario: Historical-source admission admits the record's refs

- **WHEN** historical-source admission reads a completed rebuild's result
- **THEN** it admits the refs that the record declares

#### Scenario: Absent originals answer unknown

- **WHEN** the side repository is empty or deleted
- **THEN** every reader that asks for a rebuild edge, the attested archive transition and marker
  pairing included, answers `unknown` by a fixed gap rather than reporting no relation
- **AND** proof admission of a later head refuses `unknown` instead of admitting a proof without its
  commitment

### Requirement: Rebuild verification caches a verdict that holds no value

Verification SHALL cache its verdict under the rebuild's directory, keyed by the record blob, the
sorted declared ref pairs, the trust-anchor digest, the runtime identity, the bundle digest and the
object format, and SHALL memoize it per invocation scope. A cache hit SHALL skip only signature
verification, and cache files SHALL hold no value.

#### Scenario: A cache hit still needs the originals

- **WHEN** the verdict cache holds a verdict under the same key
- **THEN** verification skips only signature verification and still requires the originals to be
  present
- **AND** the cache files hold no value

### Requirement: Rebuilt refs publish into a re-created peer by creation

Each rebuilt branch, re-created tag and kept ref that the record says a peer held and that ETHOS
publishes SHALL publish into that peer, once it is re-created and empty, by creation under a
zero-value lease. No peer SHALL receive an object that holds a declared item, and
`refs/ethos/attestations-set` SHALL be neither rewritten nor published.

#### Scenario: Rebuilt refs publish into an empty peer

- **WHEN** a re-created peer holds no ref, and the record says that peer held a rebuilt branch,
  re-created tag or kept ref that ETHOS publishes
- **THEN** publication creates each such ref under a zero-value lease
- **AND** no object it sends holds a declared item, and `refs/ethos/attestations-set` is not
  published

#### Scenario: Branches go before tags

- **WHEN** publication sends a rebuild's branches and re-created tags into a re-created peer
- **THEN** it sends the branches first, and the re-created tags that no published branch reaches
  oldest first
- **AND** when the publication owner classifies the peer's refusal of a branch's push as
  `publication_pack_refused:<peer>`, the plan's next step sends that branch's reachable re-created
  tags oldest first, then the branch

#### Scenario: Each pack step is recorded

- **WHEN** the rehearsal publishes the plan into the declared rehearsal peer
- **THEN** it records each step's pack size, so a step that a re-created peer later refuses is named
  by that size
- **AND** ETHOS declares no pack limit of its own, and rebuild readiness measures no pack

#### Scenario: A `retag` ref waits for its re-created tag

- **WHEN** publication is asked for a declared `retag` ref whose current value still equals its
  recorded old value
- **THEN** the rebuild's publication admission refuses it by a fixed gap that names the ref,
  whatever the push check's mode
- **AND** once `land --retag` has recorded the re-created tag, publication admits the ref

#### Scenario: A peer that keeps an original tag refuses

- **WHEN** a peer still holds an original tag object under the name of a re-created tag
- **THEN** publication of that tag refuses with `release_tag_immutable` and the peer's tag is kept

#### Scenario: A raw mirror push refuses

- **WHEN** `git push --mirror` of a rebuilt repository runs through the installed pre-push hook
- **THEN** the hook refuses the push
