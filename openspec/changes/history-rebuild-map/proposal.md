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

This Change is landing 1 of the rebuild: it is effect-free and ships in beta.9. Landing 2 opens its
own Change.

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
  ref outside `refs/heads/` and `refs/tags/` can only retire. Prewrite admits the record for the
  selected Change only.

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
- **One key-generation owner.** Redaction and readiness read the repository's last recorded key
  generation through one owner in `adapters/repo`, and readiness refuses a key of another
  generation.
- **The catalog entry.** `lane repair-signature` gains the census and rebuild readiness operations
  ahead of today's signature modes; `--expect-head` is required only where an operation takes it.
- **Permanent provenance.** Records under the `rebuild:<id>` lifetime key never end, like DR-0018's
  historical artifact attestations.
- **Budget.** In this lane: DR-0020's product revisit, recorded in DR-0024's Evidence, and DR-0010's
  Evidence naming landing 2's removals; the test step is DR-0023's. Every figure is measured here.
- **Landing 2, in its own Change.** The local apply with its owner-only side store, the keyless
  verification and record-resolution owners that every reader goes through, publication into
  re-created peers, `--release` and `--rollback`. It starts from this Change's reviewed text,
  preserved at `ed3c367e2`. One Change per landing keeps each Change's artifacts within the 500-line
  document ceiling, and this Change's archive adds only the requirements that landing 1 implements.

**Breaking:** `lane redact private-addresses --verify` re-derives with the one scan, so re-verifying
an earlier redaction whose base held a crossing entry or a percent-encoded fed path reports
`redaction_unverified`; recorded attestations stay valid. `--corrections` keeps its request and its
history write path. Out of scope: deleting and re-creating forge projects, restoring Releases,
assets and CI settings, publishing lightweight tags, replacing a published tag in place, renaming
tree entries, reading a credential store, re-pointing submodules, scanning or re-uploading LFS
objects, and copies outside the rebuilt refs.

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
    - `Rebuild reports carry no identity`
  - MODIFIED:
    - `Attestation lifetimes end with the transition that consumes them` (the permanent
      `rebuild:<id>` key)
    - `Remote publication observations preserve epistemic state` (namespaces, no stderr)
- `repository-paradigm`: MODIFIED `OpenSpec carries the common rules` (the `[openspec]` table
  declares `rebuild.toml`), `Peer identity markers are keyed, canonical and shared` (the one scan,
  named contexts, record span kinds and citations as data) and
  `Marker edits in record roots reproduce what they replace` (encoded paths and citations pair).
- `command-plane`: MODIFIED `Result projection preserves diagnostic execution facts` (a peer
  observation's failure carries no remote stderr; local tools keep theirs), and MODIFIED
  `Accepted signature repair command`, with rebuild readiness, `--census` and their operations. Its
  scenarios "Exact selection and backup", "Only authorized bytes change" and "Re-entry after repair"
  are scoped to signature and identity repair, since `--corrections` stays.
- `assistant-projections`: MODIFIED `Agent projections preserve native Change ownership`, for the
  prewrite admission of `rebuild.toml`.

## Impact

- **Size:** at `f420780e8`, landing 1 and the batch's two small Changes take the product from
  77,745 to 79,737 line-equivalents and the tests from 99,942 to 101,764; the small Changes add 30
  and 43 of them.
- **New modules:** `adapters/repo/commit/rebuild/`, `repository/rebuild_record.py` and
  `adapters/repo/key_generation.py`.
- **Extended:**
  - `observe_remote_refs`, with proposal absorption and the push check reading through it;
  - `peer_identity.py`: the one scan, `_SPAN`, named contexts, the occurrence model and pre-images;
  - the record-marker verifier;
  - the diagnostic facts of a failed peer observation;
  - the redaction verb, which reads the key generation through its owner;
  - the `lane repair-signature` catalog entry;
  - the lifetime classifier;
  - the paradigm's `[openspec]` table and the OpenSpec bootstrap admission.
- **Records:** DR-0024, which also holds DR-0020's revisit outcome, and a DR-0010 Evidence entry for
  landing 2's test removals.
- **Order:** after catalog-groups, which converted `lane repair-signature` and is archived on dev;
  this Change ships in beta.9, and landing 2's Change follows.
- **Adopters:** aigw-cli applies after the release that ships landing 2, then the proxy.
