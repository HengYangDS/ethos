# Proposal

## Why

Two adopters must remove two kinds of identity from their published Git history:

- attribution trailers;
- a private forge's peer identity: hosts, ports, namespaces, merge-request citations and project
  IDs.

The adopters are aigw-cli first and openai-responses-proxy second. Their owner decided on 2026-11-05
and 2026-11-10 to rewrite each history once and to re-create both forge projects of each repository
outside ETHOS; for the proxy, AIGW reconfirms the re-creation before its rebuild.

ETHOS's `repair-signature` moves every ref to one value, walks only from the accepted head and
rewrites no file contents, so it cannot do this. rc-plan Appendix G designs the rebuild, and its
prerequisites F and A3 are on dev. A read-only sizing and five reviews found the code paths that
refuse today's plan. This Change restates the design with those repairs.

## What Changes

- **A Change-local record.** `rebuild.toml` is landed by a normal signed landing. For every local
  ref outside a short allowlist it declares:
  - the disposition: `rebuild`, `retag`, `retire`, or `keep` for a ref that is not affected, one no
    object of which, its own tag object included, holds a declared item or trailer;
  - the local old value, named by ID only when today's trust anchor verifies the original's
    signature, and otherwise by keyed digest;
  - each peer's expected state.

  It names its key only by F's generation, which must also be the repository's last recorded one,
  and it names no credential store. Its transform entries are keyed digests of typed pre-images,
  each with the count of results that F's one scan attributes to it; hosts, paths and ports carry
  witnesses that name one scan result in a commit's or a tag's message or in a blob at a path. IDs
  name contexts from F's named set, and `retain` prefixes are clear public path prefixes with no
  count. Version 1 freezes the occurrence rules, so the record is not re-landed after landing 2. A
  ref outside `refs/heads/` and `refs/tags/` can only retire.

- **Grammar.** F's grammar moves to one left-to-right scan for every reader, widens its keyless span
  shape to encoded paths and citations, names its contexts, and defines the occurrence model and the
  pre-images as data.
- **Readiness.** It walks every declared ref's originals and refuses before the owner deletes
  anything: undeclared spans and feed values, items in headers or tree entry names, wrong counts,
  misplaced witnesses, clear IDs of unsigned originals, history that the walk cannot see, a `retag`
  of a tag whose target is unaffected or that targets another tag, an ambiguous quoted ID, and refs
  that could not publish. It reports by count and fixed gap name only, including each entry's
  discovered count and each `retain` prefix's occurrence total by index, and quoted IDs per object
  by kind. A keyless mode, `--census`, takes no record and no key, for ETHOS's own R8 (e) run.
- **One peer observer.** `observe_remote_refs` extends to namespaces, proposal absorption and the
  push check read through it, and no failure report carries the remote's stderr, while a local tool
  keeps its own.
- **A local apply.** The apply:
  - reads the peers only;
  - keeps originals in an owner-only side store;
  - rewrites blobs, trees and messages, follows content digests, maps every quoted ID of a rewritten
    commit or tag to its image, so no original ID survives, and prepares each re-created tag's
    message without any signature armor;
  - signs commits in order;
  - proves, before any ref moves, that nothing reachable from the result, from a kept ref or from a
    prepared message holds a declared item;
  - moves every `rebuild` and `retire` ref to its own value in one transaction, and holds each
    `retag` target under `rebuilt/` until `land --retag` re-creates the tag from the prepared
    message.

  Only readiness and the apply read the key.

- **One verification owner and one record-resolution owner, both keyless.** Every reader goes
  through them: the hook, historical source, retag, release, publication, conservation, archive
  provenance and marker pairing. They verify the record's binding, the signed records, the
  structural bijection and the private-address scan, and recompute no transform. Under a record
  root, a rebuilt blob passes marker pairing only when it equals its original with exactly the
  declared items replaced.
- **Publication into re-created peers, `--release` and `--rollback`.** A rebuilt branch's introduced
  range starts at the verified image of its declared old value, and a re-created tag pushed before
  any branch that reaches it starts at the verified image of its original target, so publishing into
  an empty peer re-judges nothing the rebuild produced. Branches go before tags; when the
  publication owner classifies a peer's refusal as a size refusal, by fixed forge patterns and
  without echoing its stderr, the plan's next step sends that branch's reachable tags first, and the
  rehearsal records each step's pack size. ETHOS declares no pack limit. A declared `retag` ref
  publishes only after `land --retag` records its re-created tag. `ethos publish` records each
  retired tag's first observed absence. `--release` previews, then requires every due receipt and
  absence. `--rollback` restores every declared old value until the owner deletes the old projects,
  and its preview blocks when a peer has left the record's declared state.
- **The catalog entry.** `lane repair-signature` gains one operation each for the census, rebuild
  readiness and apply, rollback preview and apply, and release preview and apply, ahead of today's
  signature modes; `--expect-head` is required only where an operation takes it.
- **Permanent provenance.** The `rebuild:<id>` records never end, like DR-0018's historical artifact
  attestations, and record retirement plans no rebuild kind.
- **Two landings.**
  - Landing 1: record, grammar, binding, the peer observer, the generation owner's read, readiness,
    keyless readiness and the transform without writes. It ships in beta.9.
  - Landing 2: the apply and the readers, together.
- **Budget.** In landing 1's lane: DR-0020's product revisit, recorded in DR-0024's Evidence, and
  DR-0010's Evidence naming landing 2's removals; the test step is DR-0023's. Every figure is
  measured at landing 1.

No breaking change: `--corrections` keeps its request and its history write path. Out of scope:
deleting and re-creating forge projects, restoring Releases, assets and CI settings, publishing
lightweight tags, replacing a published tag in place, renaming tree entries, reading a credential
store, re-pointing submodules, scanning or re-uploading LFS objects, and copies outside the rebuilt
refs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`:
  - ADDED:
    - `A Change-local record authorizes one history rebuild`
    - `A rebuild record declares every ref and each peer's state`
    - `Rebuild transform entries declare items by keyed digest`
    - `Rebuild counts and witnesses share one occurrence model`
    - `A rebuild record names an original in clear only when it is signed`
    - `Rebuild readiness proves discovered completeness before any effect`
    - `A rebuild reads its peers through one namespace listing`
    - `Keyless readiness counts identity without a record`
    - `A rebuilt history holds no declared or discovered identity`
    - `Rebuild reports carry no identity`
    - `Rebuild originals live in an owner-only side repository`
    - `Readers verify a rebuild through one owner without the key`
    - `Rebuild verification caches a verdict that holds no value`
    - `Rebuilt refs publish into a re-created peer by creation`
  - MODIFIED:
    - `Commit policy applies to exact introduced commit ranges` (rebuilt branch and re-created tag
      baselines)
    - `Bounded accepted signature replacement`
    - `Publication composes historical repair with forward integration`
    - `Attestation lifetimes end with the transition that consumes them`
    - `Accepted history repair preserves original acceptance provenance`
    - `A repaired release tag is re-created on its replacement commit`
    - `A re-created release tag publishes on its original qualification`
    - `Remote publication observations preserve epistemic state` (namespaces, no stderr)
- `repository-paradigm`: MODIFIED `OpenSpec carries the common rules` (the `[openspec]` table
  declares `rebuild.toml`), `Peer identity markers are keyed, canonical and shared` (the one scan,
  named contexts, record span kinds and citations as data) and
  `Marker edits in record roots reproduce what they replace` (a rebuilt blob passes only as its
  original with exactly the declared items replaced; encoded paths and citations pair).
- `command-plane`: MODIFIED `Result projection preserves diagnostic execution facts` (a peer
  observation's failure carries no remote stderr; local tools keep theirs), and MODIFIED
  `Accepted signature repair command`, with `--rebuild`, `--rollback`, `--release` and `--census`
  and their operations. Its scenarios "Exact selection and backup", "Only authorized bytes change"
  and "Re-entry after repair" are scoped to signature and identity repair, since `--corrections`
  stays, and gain rebuild counterparts.
- `assistant-projections`: MODIFIED `Agent projections preserve native Change ownership`, for the
  prewrite admission of `rebuild.toml`.

## Impact

- **Size (estimates):** product +1,288 to +2,015 line-equivalents and tests +938 to +1,390, in two
  landings, the second split into two review and proof slices; landing 1's figures are measured in
  its lane.
- **New modules:** `adapters/repo/commit/rebuild/` and `adapters/mutation/accepted/rebuild.py`.
- **Extended:**
  - `completed_signature_repair` and `_verify_backup_recovery`;
  - `observe_history_repair_mapping`;
  - `observe_remote_refs`, with proposal absorption and the push check reading through it;
  - `peer_identity.py`: the one scan, `_SPAN`, named contexts, the occurrence model and pre-images;
  - the record-marker verifier;
  - the diagnostic facts of a failed peer observation;
  - one key-generation owner in `adapters/repo`, which redaction calls;
  - the `lane repair-signature` catalog entry;
  - the commit-range baseline;
  - `release.py`, `retag.py` and archive provenance;
  - the lifetime classifier;
  - the paradigm's `[openspec]` table.
- **Records:** DR-0024, which also holds DR-0020's revisit outcome, and a DR-0010 Evidence entry for
  landing 2's test removals.
- **Order:** after catalog-groups, which converted `lane repair-signature` and is archived on dev;
  landing 1 ships in beta.9.
- **Adopters:** aigw-cli applies after the release that ships landing 2, then the proxy.
