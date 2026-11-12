---
subject: ethos:decision:history-rebuild-map
role: decision
state: canonical
decision_id: DR-0024
decision_status: accepted
relations:
  current_owner: ../../openspec/specs/repository-governance/spec.md
---

# DR-0024: History Is Rebuilt Once, Under One Change-Local Record, With Originals Held Locally

Status: canonical rationale. The repository-governance, repository-paradigm and command-plane
specifications own current behavior.

Date: 2026-11-12.

Purpose: preserve why ETHOS rebuilds an adopter's published history once under a landed record, why
the originals stay in a local side repository until the owner deletes it, why only readiness and the
apply read the key, why the record names an unsigned original only by keyed digest, why the work
lands in two landings, and what stays outside ETHOS.

See also: [DR-0010: Source-budget non-compensation](dr-0010-source-budget-non-compensation.md),
[DR-0017: One obligation, one owner](dr-0017-one-obligation-one-owner.md),
[DR-0018: A historical artifact is judged by the attestation made when it was
produced](dr-0018-historical-artifact-attestation.md),
[DR-0019: The source budget counts code, not layout](dr-0019-layout-invariant-source-budget.md),
[DR-0020: The product ceiling moves to 80,000 for the RC work](dr-0020-product-budget-step.md), the
`history-rebuild-map` OpenSpec Change and the
[repository-governance specification](../../openspec/specs/repository-governance/spec.md).

## Context

Two adopters, aigw-cli first and openai-responses-proxy second, must remove two kinds of identity
from their published Git history: attribution trailers, and a private forge's peer identity, that is
its hosts, ports, namespaces, merge-request citations and project IDs. Their owner decided on
2026-11-05 and 2026-11-10 to rewrite each history once and to delete and re-create both forge
projects of each repository outside ETHOS. For the proxy, AIGW reconfirms the project re-creation
before its rebuild. The owner delegated the remaining design choices to the design's author, 97f828,
who took them on 2026-11-11 in five sets, the last three after a fifth independent review.

ETHOS's signature repair cannot do this. It moves every ref to one value, it walks only from the
accepted head, so re-tagging and release provenance see only repairs under that head, and it
rewrites no blob, tree or message span. Its prerequisites are on dev: F, the keyed peer identity
grammar and marker, and A3, which re-creates a repaired release tag on its replacement commit. The
rc-plan's Appendix G designed the rebuild. A read-only sizing and five reviews then found the code
paths that refused that plan, and the `history-rebuild-map` Change restates it with their repairs.

The rebuild gates no release candidate; it serves the two adopters. R8 (e) still asks ETHOS to scan
its own history and record the disposition. At `d8474ec31` the product measured 77,482 of its 80,000
line-equivalent ceiling and the tests 99,842 of their 100,000, while the Change was estimated at
1,288 to 2,015 product and 938 to 1,390 test line-equivalents. Landing 1 ships in beta.9. At its
lane base `d72001921` the product measured 77,745 and the tests 99,942, the tests now under
DR-0023's 105,000; landing 1 takes them to 79,737 and 101,764 at `f420780e8`.

## Decision

- **One record is the authority.** A rebuild is authorized only by `rebuild.toml` in the authorizing
  Change, landed by a normal signed landing, and version 1 is complete in landing 1. Its refs table
  declares every local ref outside a short allowlist with its disposition, its local old value and,
  per peer, its expected state: that value, a declared peer value or absent. Dev, main and
  candidate/dev are declared at the accepted head rather than by value, since the record lands in
  that head itself. The record binds only when its blob is the same in the accepted head and in the
  rebuilt image, the landings since its base touch only its Change and the refs that move are its
  own; its expiry gates only a new apply. No flag, receipt or peer state stands in for it.
- **One occurrence model counts and locates every item.** F's grammar scans each object's bytes in
  one left-to-right pass, commit messages, annotated tag messages and blob contents only, and gives
  each result to exactly one entry, the longest declared entry at its position. Every entry but a
  retained prefix is the keyed digest of its kind's own pre-image, with the count of the results
  attributed to it over every distinct object that the declared old values reach. A host, path or
  port carries a witness that names one such result in a commit's or a tag's message or in the blob
  at a path in a commit's tree, so no blob or tree is named by its own ID, and the counts and the
  witnesses agree by construction. The witnesses live in the record blob, which the signed landing
  commit signs. A declared item in any commit or tag header or in a tree entry name refuses, since
  the transform rewrites no identity header and renames nothing. Version 1 freezes these rules, so a
  record is not re-landed after a later release, and a change to them takes a new record version.
- **An original is named in clear only when it is signed.** A witness object, an old value, a
  declared peer value and the record's base are named by ID only when that commit or tag carries a
  signature that today's trust anchor verifies; an original that today's anchor does not verify is
  treated as unsigned, whatever policy held when it was made. Any other original is named by a keyed
  digest of its ID; readiness and the apply resolve it with the key, and the apply records its clear
  ID only in its signed local attempt record, which is never published. The apply's prepared tag
  messages drop every signature armor that ETHOS knows, SSH, OpenPGP and X.509, so no original's
  signature returns with the re-created tag.
- **Contexts are named in F's grammar, and retained prefixes are public.** An ID names its contexts
  from F's named set; a context an adopter needs joins that set as data, with a test, so every
  keyless reader and the push check see it. A retained prefix is a clear public path prefix after a
  declared host, port or scp colon: the host is still replaced, the prefix stays, and the rest is
  still scanned. A retained prefix carries no count; readiness reports its occurrence total for the
  owner's review. The declared public-distribution peer's path bounds the declared paths.
- **The key is named only by its generation.** The record names its key by F's generation, which
  names a key without revealing it, and no credential store. Readiness and the apply refuse a key
  whose generation differs from the record's or from the repository's last recorded one, which one
  owner reads from both the redaction records and the rebuild attempt records. Redaction calls the
  same owner, so a later redaction must use the same key unless it rotates, and no redaction record
  is written without a redaction.
- **Each ref gets its own value and disposition.** Today's repair gives every ref one value; a
  rebuild moves each declared ref to its own value in one ref transaction. A branch is rebuilt, an
  annotated tag's rebuilt target is held under `refs/ethos/rebuild/<id>/rebuilt/` until the re-tag
  re-creates the tag, a retired ref is removed, and a kept ref publishes as it is. A ref is affected
  when any object it reaches, its own tag object included, holds a declared item or trailer, and
  only an unaffected ref may be kept. A ref declared for rebuilding or re-tagging that reaches no
  affected object refuses, so what is rewritten is what is affected. A lightweight tag can only
  retire, and so can a ref outside branches and tags, such as notes, replace refs, the stash and
  prefetch refs. A tag whose target is unaffected, or whose object targets another tag, cannot be
  re-tagged: readiness points it to retire, and the owner re-creates it by hand afterwards if it is
  wanted.
- **Only readiness and the apply read the key.** Readiness recomputes the transform in memory, and
  the apply checks the key against every witness and every count before it writes anything. The
  apply transforms each re-tagged tag's message and keeps it in its signed result record; the re-tag
  reads that message without the key and owns only the tag's creation and policy. Every other reader
  verifies without the key, through the record's binding, the signed attempt and result records
  whose witness check bound the key, the structural bijection, in which parents, dates, authors and
  committers are byte-equal and only the named objects differ, and the private-address scan.
- **Readiness refuses before the owner deletes anything.** It walks every declared ref's originals
  once and computes the rebuilt image in memory. It refuses every discovered span and every value of
  F's local feed, current or former, that no entry declares or retains, so it refuses what the push
  check would refuse at publication. It also refuses an item in a header or a tree entry name, a
  count that differs from the record's, a misplaced witness, a clear ID of an unsigned original, a
  retained prefix that could hide identity, every ref or peer that differs from the record, every
  ref that could not publish afterwards, and history that its walk cannot see: a shallow repository,
  grafts, a linked worktree with a detached HEAD or a per-worktree ref. It counts quoted IDs per
  object by kind and refuses a quoted token that prefixes two or more rewritten objects. It reports
  only counts and fixed gap names and records nothing.
- **The rebuilt objects are proved before any ref moves.** Nothing reachable from a rebuilt branch,
  a tag's rebuilt target or a kept ref, and no transformed tag message, may hold a declared item, an
  undeclared discovered span or a private-class address, and every rebuilt ref must be connected
  without the side repository. Content digests follow the files whose bytes the transform changed,
  and every quoted ID of a rewritten commit or tag is mapped to its image's ID at the same length,
  so no original ID survives in the rebuilt history, signed or not, and archive evidence keeps
  resolving. The re-tag proves the same for each tag it creates.
- **The originals are held locally.** After the key verifies against every witness, the apply keeps
  the originals in `<common>/ethos/rebuild/<id>/originals.git`: owner-only, never a remote, with no
  alternates either way and each old value under its own ref. Readers attach it read-only per Git
  process. Its exit is a recorded release of the rebuild plus the owner's decision to delete it, and
  ETHOS's reports say "originals held locally", never "purged". Afterwards a reader that asks for a
  rebuild edge answers unknown, and the rebuilt commits remain ordinary signed history for every
  other reader.
- **The records are permanent provenance.** The `rebuild:<id>` records, the attempt, the result, the
  applied ref update, each observed absence and the release, have no end condition, as DR-0018's
  historical artifact attestations have none, and record retirement plans no rebuild kind.
- **A re-created tag keeps its original qualification.** Following DR-0018, a re-created tag,
  including one on an older commit or a maintenance release, publishes on its original qualification
  verified through the rebuild's bijection. The rebuilt commits are not re-judged under today's
  commit policy, F's keyless verifier or today's CHANGELOG grammar, which 9 of the first adopter's
  33 release tags predate.
- **Publication into a re-created peer re-judges nothing the rebuild produced.** A rebuilt branch's
  introduced range starts at the verified image of its declared old value, whatever the peer holds,
  and a re-created tag pushed before any branch that reaches it starts at the verified image of its
  original target. Branches publish before tags. ETHOS declares no pack limit of its own: when the
  publication owner classifies a peer's refusal of a branch's push as a size refusal, by fixed forge
  patterns that it holds and without echoing a byte of the peer's stderr, the next step sends that
  branch's reachable re-created tags oldest first, then the branch, and the rehearsal records each
  step's pack size so a refused step is named. A declared re-tag ref publishes only after the re-tag
  records its re-created tag, whatever the push check's mode. Under a record root, a rebuilt blob
  passes marker pairing only when it equals its original with exactly the declared items replaced,
  checked through the bijection while the originals are present.
- **One observer reads every peer.** The publication observer extends from exact refs to namespaces;
  the rebuild, proposal absorption and the push check read through it, and none of its failure
  reports carries the remote's stderr, which can name a peer's address, while a local tool's failure
  keeps its own.
- **Release and rollback close the transition.** Publication records a retired tag's first observed
  absence on a re-created peer, which becomes that peer's latest state, so lifetime observation
  keeps working after the owner's garbage collection. The release of a rebuild previews first; its
  apply records any absence that publication missed, needs a publication receipt wherever the record
  says a peer held a ref that ETHOS publishes, so none for candidate/dev, and the recorded absence
  of every retired tag, and then deletes only the `rebuilt/` refs. Rollback restores every declared
  old value from the side repository until the owner deletes the old forge projects. Its preview
  refuses when a declared ref has left its recorded rebuilt value, and blocks, naming the ref and
  the peer, when a peer has left the record's declared state. The applies of the rebuild, the
  release and the rollback are destructive under ordinary authorization, each its own operation of
  the repair command, and a head is required only where an operation takes one.
- **Two landings.** Landing 1 ships the record, the grammar's one scan and named contexts, the
  binding, the peer observer, the generation owner's read, the transform without writes, readiness
  with its publishability checks and keyless readiness; it is effect-free and releasable, and it
  ships in beta.9. Landing 2 ships the apply, verification, the readers, the push baselines, the
  strict marker pairing, release, rollback and the pack steps as one candidate with two review and
  proof slices, so no release ships an apply whose re-created tags cannot publish.
- **ETHOS's own R8 (e) run is keyless.** It is a read-only mode of the repair command, proposed as
  `--census`, with no record and no key: the local feed, F's grammar and the trailer rule are its
  inputs, and counts by form and ref class its output. It runs over ETHOS's local refs and so
  deliberately restates Appendix G's "readiness scan over its own declared refs". Counts, at
  `d72001921` over its 62 local refs (13,328 commits and 42,500 blobs of 788 MB, walked in 2,132 s):
  the branches, the tags and the remote-tracking refs each reach 169 `authority`, 5 `manual` and 4
  `path` occurrences of the private forge's identity, and the other local refs, such as
  `refs/keep/*`, reach 169 `authority`, 10 `manual`, 6 `path`, 207 `url` and 3 attribution trailers.
  No ref was left unwalked, and the current tree holds no occurrence of the forge's host, a
  private-network address. Disposition: ETHOS's own history is not rebuilt in 0.2.0. The push check
  refuses new occurrences, so the published history no longer grows them, and that history is the
  provenance root of every adopter's pinned runtime and of its 34 tag objects: a rebuild waits until
  landing 2's apply has rebuilt aigw-cli and openai-responses-proxy, and the owner then decides
  whether ETHOS rebuilds its own history under its own record.
- **The budget is settled in landing 1's lane.** DR-0020's product revisit happens there, since
  landing 1 alone may cross its 78,000 trigger, and its outcome is recorded in this record's
  Evidence. The test ceiling is already at 105,000 under DR-0023, taken for this record and the
  budget's role categories together; DR-0010's Evidence names landing 2's test removals and their
  expected sizes, namely the bundle-based re-tag tests and the fixtures repeated across the
  history-repair test modules, with DR-0019's revisit outcome. Every figure is measured at landing 1
  and names its commit.

## Alternatives Rejected

- **Extend today's repair:** one value for every ref, a walk from the accepted head only and no
  rewrite of blobs, trees or messages cannot reach tags off dev or remove an identity from a file.
- **Replace the published tags in place on the old peers** (`published-tag-replacement`): not
  pursued, since the rebuild re-creates both peers and ETHOS publishes into them empty.
- **Marker literals in the record:** archiving the authorizing Change moves `rebuild.toml` under the
  archive root, where each added marker line refuses `record_marker_unpaired`; a 64-hex digest is no
  marker.
- **A witness that names a blob by its ID, with an offset and a length:** a blob's ID is an unkeyed
  digest, so a small blob can be enumerated from it, and the offset and length give the item's place
  and size.
- **A witness counted in a per-commit discovery order:** it defined no occurrence universe per entry
  kind, could not reach an item that lives only in a tag object, and counted differently from the
  entry counts.
- **Naming every original by its ID:** an unsigned commit or tag can be enumerated from its ID once
  the rebuilt image and its parents are known, because a private literal has little entropy.
- **Context frames written in the record:** the keyless readers and the push check know only F's
  named set, so an ID replaced in a record frame would be invisible to them; a needed context joins
  the named set instead.
- **A keyed retained prefix that starts at a host:** it refused exactly the public path after a
  declared host that it was meant to keep, and where it did apply it kept a whole span in clear.
- **A credential-store reference in the record, a service and an account:** ETHOS never reads a
  credential store, and F's generation already names a key without revealing it.
- **A new predicate for the rebuild's key generation, or a redaction record without a redaction:**
  the generation owner reads the rebuild attempt records directly, and a redaction record would
  claim a verified redaction that never ran.
- **A separate signature on each witness:** the record blob holds the witnesses, and the signed
  landing commit that lands it signs them.
- **One expected state for every peer:** the first adopter's two peers disagree on some tags, 11
  release candidate tags on one of them, so each peer's state is declared, a declared peer value
  included.
- **Readers that recompute the transform:** recomputing needs the key, which would then reach every
  hook, re-tag and publication. Readers verify the signed records and the structural bijection
  instead, and recomputing stays readiness's job.
- **The re-tag transforming its own message:** it would need the key. The apply prepares the
  message, proves it with the rest of the rebuilt objects and records it, and the re-tag owns
  creation and policy.
- **Records with an end condition, such as an owner purge or the originals' absence:** the purge
  happens outside ETHOS and nothing records it, and records that ended would leave readers unable to
  answer unknown, so an archived intent would fail open. The records are permanent instead.
- **Restoring each original from the backup bundle at re-tag time:** after the owner's garbage
  collection every reader needs the originals, so one side repository serves them all and the bundle
  restore retires.
- **Attaching the side repository to lifetime observation to keep old receipts current:** it would
  hide the gap only until the side repository is deleted; the observed absence becomes the peer's
  latest state instead.
- **Re-judging rebuilt commits and re-created tags under the current policy, or starting a pushed
  ref's range at the peer's state:** it contradicts DR-0018, and on an empty peer it would re-judge
  the whole rebuilt history, refusing tags that predate today's CHANGELOG grammar and rebuilt
  commits whose archived Changes now carry markers.
- **Admitting any record-root line whose markers the record declares:** it would also admit changed
  words around a marker, so a rebuilt blob passes only as its original with exactly the declared
  items replaced.
- **A count for a retained prefix:** a count binds a declared item's occurrences so the apply can
  refuse drift, while a retained prefix is public text that stays.
- **Judging an original's signature under the policy that held when it was made:** the rule protects
  what the rebuilt history publishes now, and the verification owner already judges against today's
  anchor.
- **A pack limit declared in the release binding:** a declared limit could drift from the forge's,
  while the peer's own refusal cannot.
- **Keeping quoted original IDs, or only counting them:** a kept ID dangles, and for an unsigned
  original it is the oracle that the record avoids; mapping each quote to its image keeps archive
  evidence resolving.
- **Leaving the early publication of a re-tag ref to F's push check:** that check refuses it only in
  the required mode.
- **Re-tagging a tag whose target is unaffected, or whose object targets another tag:** a re-tag
  needs a mapped target and re-creates one level on the peeled commit, so readiness points such a
  tag to retire.
- **Measuring packs in readiness:** readiness writes no object and runs before the apply, so a
  peer's own size refusal at publication decides instead, against the pack sizes that the rehearsal
  records.
- **Re-observing the old peers with readiness after the apply:** readiness cannot pass once the refs
  are in their rebuilt states; a rollback preview compares the old peers with the record instead.
- **Releasing the apply on its own:** a user could apply and not finish, since re-created tags other
  than the tip's could not publish and the release step would not exist.
- **Asking for an irreversibility confirmation on the applies:** the point of no return is the
  owner's deletion of the old forge projects, outside ETHOS, so ordinary authorization suffices.
- **Converting identity corrections into a transform kind now:** it would break existing correction
  requests, so `--corrections` stays a separate history write path under the same command until its
  follow-up.

## Consequences and Boundary

- **Outside ETHOS:** deleting and re-creating forge projects, restoring Releases and their assets,
  and CI settings in the re-created projects are the adopter's. The owner decides which release
  assets whose bytes hold an identity form to restore, and ETHOS neither scans nor publishes them.
  ETHOS publishes no lightweight tag, replaces no published tag in place, renames no tree entry and
  reads no credential store. A submodule whose URL held a declared item points at a marker that no
  longer resolves, and ETHOS neither scans nor re-uploads LFS objects; both are the adopter's.
  Copies outside the rebuilt refs, such as forks, Software Heritage and GH Archive, stay as they
  are, as do the peers' review refs whose objects are not local: readiness counts those it can see
  and reports the rest as unknown, and only deleting a project removes them.
- **The side repository holds every original identity in clear** until the owner deletes it, so it
  is owner-only, and the adopter copies the backup bundle to a second device before the owner
  deletes the projects.
- **The key stays with readiness and the apply, and it is the repository's one recorded key.** No
  hook, re-tag, publication or release reads it, so a reader cannot check a digest against its
  witness and relies on the apply's signed records.
- **The record stays in the rebuilt history,** with its digests, counts, context names, witnesses
  and clear retained prefixes, and it names an original by ID only when that original is signed.
- **The shared grammar changes in landing 1:** the redaction verb, the push check and the keyless
  verifier move to the one scan, and a context an adopter needs joins the named set as data.
- **The peer observer's failure reports carry no stderr** for any caller.
- **Quoted IDs of originals are rewritten:** every quote of a rewritten commit or tag becomes its
  image's ID at the same length, and an ambiguous quote refuses readiness.
- **The records grow and never end:** every rebuild adds its records to the attestation store for
  good.
- **The point of no return** is the owner's deletion of the old forge projects; rollback exists
  until then.
- **A window remains:** between the owner's garbage collection and the first observation of a
  retired tag's absence, lifetime observation of that ref stays unknown, so the migration publishes
  first.
- **Two history write paths share one command:** `--corrections` stays beside `--rebuild`, a known
  deviation from DR-0017's single owner. Owner 97f828, review 2026-11-24, next action a design note
  on expressing corrections as transform kinds with a migration for existing requests.
- **Costs and limits:** scanning the first adopter's blobs takes about 48 s by inference and is
  memoized. On an empty peer whose mode is required, the peer identity push check scans the whole
  history once per peer. GitHub accepts packs up to 2 GiB with a 100 MiB per-file limit, and an
  adopter's GitLab refused a push over 20 MiB, so a rehearsal against a declared rehearsal peer
  records every step's pack size, and a peer's own size refusal leads to the tag-stepped order. An
  SSH remote with a locked key can reach the terminal until the 30-second deadline.
- **Unproven when this record was written:** the first adopter's commit count off dev and its blob
  sizes, GitHub's push-event rule for tags, and whether the adopters' originals that the record
  names are signed; CI stays off in the re-created projects until every tag publishes.
- This record admits no budget growth by itself; the steps above are judged in landing 1's lane.

## Evidence and Revisit

- The `history-rebuild-map` Change's proposal, design and tasks; the rc-plan's Appendix G in
  `openspec/changes/archive/2026-11-07-rc-plan/design.md`; F's Change in
  `openspec/changes/archive/2026-11-08-peer-identity-redaction/` and A3's in
  `openspec/changes/archive/2026-11-05-mapped-release-retag/`; and the archived peer-address
  boundary design's reason for refusing unkeyed digests, in
  `openspec/changes/archive/2026-11-05-peer-address-boundary/design.md`.
- The census of the first adopter's refs and spans, relayed by AIGW on 2026-11-10 in labels and
  counts only and not verified independently, for the per-peer tag values; AIGW's review of design
  draft 4 on the same evening, for the 9 of 33 release tags that predate today's CHANGELOG grammar.
- The fifth independent review of the design, at dev `fdb81a373`, and the design author's three sets
  of decisions of 2026-11-11, under the owner's delegation: the first on key use, the records'
  permanence, the recorder of an observed absence and the command's forms; the second on the key's
  generation, witnesses, contexts, counts, retained prefixes, baselines, marker pairing, the
  rollback preview and the landing order; the third, after the review, on the occurrence model, the
  naming of unsigned originals, retained prefixes, the catalog entry, the peer observer, the
  generation owner and the pack steps; and the fourth, after draft 8, on retained prefixes' counts,
  unaffected-target re-tags, pack limits, the trust anchor, diagnostic facts and the operations'
  effects; and the fifth, after draft 9, on quoted original IDs, the re-tag publication refusal and
  the bounds of size-refusal classification.
- Measured in landing 1's lane, each with its commit: the lane base `d72001921`, with 77,745 product
  and 99,942 test line-equivalents; landing 1 at `f420780e8`, with 79,737 and 101,764, of which the
  batch's two small Changes, the tutorial role and the Lease supersession fix, add 30 and 43.
  DR-0020's revisit: the product passed its 78,000 trigger, so a product step, removals first and
  then one 5,000 step to 85,000 under its own decision record, lands before landing 2. DR-0023 took
  the test step, and DR-0010's Evidence names landing 2's test removals. ETHOS's keyless counts and
  disposition stand above.

Revisit at the 2026-11-24 review of the corrections follow-up, and when AIGW reconfirms or withdraws
the proxy's project re-creation. This record stands until a later decision supersedes it.
