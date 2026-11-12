# Design

See the [proposal](proposal.md). Five reviews and the author's decisions shaped this text before
the Change opened; marks such as R12, B2 or decision 17 name their items. Paths without a root
are under `src/ethos/`. Figures name their commit. The base is dev = main `d72001921`. This
Change is landing 1; decisions 7 to 16, landing 2's, keep their numbers in landing 2's own Change
(decision 17).

## Context

- **Adopters, in order:** aigw-cli, then openai-responses-proxy (owner decisions of 2026-11-05 and
  2026-11-10).
  - aigw-cli re-creates both forge projects.
  - For the proxy, "rebuild both repositories" stands, and AIGW reconfirms its project re-creation
    before the proxy's rebuild (pending; census section 8).
- **Today's repair:**
  - It moves every ref to one value (`adapters/repo/commit/signature.py:317-318`).
  - It walks only from the accepted head, and retag and release provenance read only repairs under
    that head.
  - It rewrites no blob, tree or message span (`adapters/repo/commit/history.py:117-137`).
- **Publishing a normally accepted head into a ref-less peer works:** absent refs are created under
  a zero-value lease (`tests/unit/cli/land/test_release.py:281-320`; R12). Landing 2 proves the
  rebuilt case (A17) on its decision 13's baselines.
- **Budgets.** At `d8474ec31`, lane 1's batch-25 head, which landed on 2026-11-10 and is an ancestor
  of dev: product 77,482 of 80,000, tests 99,842 of 100,000. Estimates for G: product +1,288 to
  +2,015, tests +938 to +1,390. Landing 1 follows `go-own-root` and `beta-7-release` (decision 17),
  so its own figures are measured in its lane: at the lane base `d72001921` the product measures
  77,745 and the tests 99,942; landing 1 at `f420780e8` measures 79,737 and 101,764, including the
  batch's two small Changes (30 and 43).

## Goals / Non-Goals

Goals:

- A Change-local record, version 1 of `rebuild.toml`, binds to its Change, its key and the originals
  of every declared ref, or refuses by a fixed gap that names no value (decisions 1 and 3).
- One left-to-right scan serves the redaction verb, F's push check, the keyless verifier and the
  rebuild's counts and witnesses, through one occurrence model (decision 2).
- Readiness proves discovered completeness by count and fixed gap and writes nothing, and the
  keyless census counts identity by form and ref class for ETHOS's own R8 (e) run (decisions 4
  and 5).
- Every peer read goes through one bounded namespace listing that records nothing and carries no
  remote stderr (decision 6).
- Landing 2's goals are its own Change's (decision 17): one apply that removes every declared item
  from the history of every declared ref, publication of the rebuilt refs into empty peers on their
  original qualification, and keyless verification by every reader.

Non-Goals:

- Deleting or re-creating forge projects, restoring Releases and their assets, and CI settings in
  the re-created projects: the adopter's, outside ETHOS.
- Replacing a published tag in place (`published-tag-replacement`): not pursued, since G re-creates
  both peers.
- Publishing lightweight tags.
- Renaming tree entries: a declared item in a tree entry name refuses (B1).
- Re-pointing a submodule whose `.gitmodules` URL holds a declared item, which becomes a marker that
  no longer resolves, and scanning or re-uploading LFS objects: the adopter's, outside ETHOS (A5 of
  review 5).
- Reading a credential store: the record names none, and the key arrives on standard input.
- Release assets whose bytes hold an identity form: the owner decides which to restore (aigw does
  not restore v0.6.1's archives); ETHOS does not scan or publish them. Copies outside the rebuilt
  refs, such as forks, Software Heritage and GH Archive, are out of scope (DR-0024).
- Converting `--corrections` into a transform kind. It stays a separate history write path under the
  same command. Its convergence is a follow-up (owner 97f828, review 2026-11-24; next action: a
  design note on expressing corrections as transform kinds with a migration for existing requests),
  so this Change ships no breaking change to it (R2 of review 1, R28).

## Decisions

### Record and grammar

1. **The record** is `rebuild.toml` in the authorizing Change, landed by a normal signed landing.
   Version 1 is complete in landing 1, and it also freezes decision 2's occurrence model, discovered
   forms and pre-images: every later runtime counts occurrences and resolves witnesses for a
   version-1 record by those rules, so the record is not re-landed after landing 2, and a change to
   them takes a new record version (A7 of review 5; draft 9). It holds:
   - `version`, `id`, `owner`, `reason`, `expires`, `base`, and `key = { generation = "<16 hex>" }`.
   - `[refs]`: every local ref outside the allowlist (A26), each with its disposition, its local old
     value, and per peer its expected state. That state is the local old value, a declared peer
     value, or `absent`; the declared peer value is how aigw's 11 GitLab rc tags are stated (B6 a).
     dev, main and candidate/dev are declared `at old` rather than by value, since the record lands
     in `old` itself (draft 8's rule; AIGW question 4). The allowlist holds
     `refs/ethos/attestations-set`, the declared refs' remote-tracking refs, a declared peer value's
     remote-tracking ref, `refs/remotes/<peer>/HEAD` resolving to one of them (B6 c) and the
     record's `rebuilt/` refs.
   - The dispositions:
     - `rebuild` (branches);
     - `retag` (annotated tags);
     - `retire`;
     - `keep`, for a ref that is not affected. A kept ref is published as it is and checked by
       `--release` (B6 b); readiness refuses a `keep` ref that ETHOS cannot publish (B8).

     A ref is affected when any object it reaches, its own tag object included, holds a declared
     item or trailer (R6), and readiness refuses `keep` of an affected ref (R6). A `rebuild` or
     `retag` that reaches no affected object refuses (A8). `retire` is admitted for any ref, so the
     owner may also retire unaffected tags (R32). A lightweight tag can therefore only retire. So
     can a ref outside `refs/heads/` and `refs/tags/` that the allowlist does not cover, such as
     `refs/notes/*`, `refs/replace/*`, `refs/stash` or `refs/prefetch/*` (A5 of review 5). Readiness
     refuses `retag` of a tag whose target is unaffected, by a fixed gap that names the ref and
     points to `retire`, and the owner re-creates such a tag by hand afterwards if it is wanted
     (draft 9). It refuses `retag` of a tag whose object targets another tag the same way, since a
     re-tag re-creates one level on the peeled commit (A5 of review 5).

   - `[transform]`: trailers and exact, owner-confirmed closing paragraphs of commit messages to
     remove (aigw's "Generated with Claude Code" paragraph on 423 commits; owner decision D1);
     hosts, paths and ports, each with a witness; typed spans; IDs with their contexts; and `retain`
     prefixes. Every entry but a `retain` prefix is a keyed 64-hex digest of decision 2's pre-image
     with its `count`, never a marker literal (R9 of review 1; B1). A `retain` prefix is clear
     public text (B3). At `old`, an item may remain only under an immutable root (G.4; A21). The
     transform never rewrites author or committer identity and renames nothing (B1).

   The record's terms, from Appendix G.2 and G.3 as the author's decisions amend them:
   - **The key (R4).** `key.generation` is F's `generation(key)`
     (`repository/paradigm/peer_identity.py:138-140`). Readiness and the apply compute the supplied
     key's generation and refuse by a fixed gap unless it equals the record's. They also refuse a
     key whose generation differs from the repository's last recorded generation, which one owner in
     `adapters/repo` reads from both `redaction:private-peer` records and `rebuild:<id>` attempt
     records. Redaction calls the same owner instead of today's private `_require_generation`
     (`application/redaction.py:287-296`), so a later redaction with another key refuses
     `redaction_key_generation_changed` unless it rotates. The rebuild apply's attempt record
     carries its generation; no new predicate exists, and no `redaction:private-peer` record is
     written without a redaction. ETHOS never reads a credential store, and the record names none.
   - **The public path (decisions after draft 7, item 6).** It has one source: the
     public-distribution peer that `release.toml` declares, resolved from its Git remote by
     `forge_web_repository` (`adapters/mutation/publication/forge.py:31`), without `key.account`. An
     unresolvable public peer refuses. A declared path entry whose digest equals the `path` image of
     the public path or of one of its segment-boundary prefixes refuses.
   - **Host entries (decisions after draft 7, item 8; R5).** In G's source draft 8 §2, a declared
     host's bytes "match the private-address pattern placed after `//`"
     (`contracts/paradigm/paradigm.toml:13`), except a former Go module host tied as an import
     path's first element, which discovery tests as if after `//`. A declared host that F's local
     feed protects is also admitted (R5). Any other declared host is "a host outside the pattern"
     and refuses.
   - **Span entries (G.2 (3)).** One entry per discovered identity span (a host, an optional port,
     at most one full path), with its witness. F's four occurrence forms, `url`, `authority`, bare
     `host` and `scp` (`repository/paradigm/peer_identity.py:264-293`), each have their own match
     context (R12). A span entry's digest is its marker's HMAC.
   - **Parts (G.2 (4)).** Typed and peer-tied: `host`, declared ports, `forge-path` (two or more
     segments, counted after decoding) and `project-id`. A namespace is tied by its leading-prefix
     occurrences after a declared host, port or scp colon, or by a merge-request citation's full
     path; its lone occurrences take its marker. The one-segment group stays, and no free strings
     exist.
   - **Witnesses (B1).** A witness is `{ object, path, n }`: the `n`-th result, counting from 1,
     that F's scan attributes to the entry in a commit's or a tag's message (no `path`), or in the
     blob at `path` in a commit's tree. A blob or tree is never named by its own ID. The object is
     reachable from a declared old value and is named as the next item says. Witnesses live in the
     record blob, which the signed landing commit signs. A misplaced witness names an object that no
     declared old value reaches, or a result whose HMAC under the key differs from the entry's
     digest. The apply checks each digest against its witness under the key and records
     `marker_digests = "verified"`, bound to the digests, the key generation and the blob (G.5 (3)).
   - **Originals are named in clear only when signed (B2).** Appendix G's rule returns: records
     "name originals by signed commit and tag IDs" (G.3). A witness object, a `[refs]` old value, a
     declared peer value and `base` are named by ID only when that commit or tag carries a signature
     that today's trust anchor verifies; an original that today's anchor does not verify is treated
     as unsigned, whatever policy held when it was made, since the rule protects what the rebuilt
     history publishes now (draft 9). Otherwise the record names it by
     `HMAC(key, "ethos.rebuild.v1\0oid\0" + oid)`, readiness and the apply resolve it among the
     reachable objects with the key, and the apply records the clear ID in its signed local attempt
     record, which is never published. Readiness refuses a clear ID whose object carries no
     signature that today's anchor verifies.
   - **ID contexts (R9).** F's `_CONTEXTS` patterns (`repository/paradigm/peer_identity.py:42-71`)
     get stable names in that module, such as `id.api-projects` and `port.url`, with no change to
     what they match. An ID entry names one or more contexts from that named set; an unknown name or
     a context named twice refuses. The record holds no context frames: a context an adopter needs,
     such as aigw's cache path, joins F's set as data in landing 1, with a test, so every keyless
     reader and the push check see it. A `project-id` is digits only, tied by one
     `CI_PROJECT_ID=<ID>` occurrence and replaced only inside a named context (G.4).
   - **Counts (B1).** A count is the number of results that F's scan attributes to the entry over
     every distinct object that the declared old values reach, each object once. Readiness reports
     each entry's count by the entry's index, never by value, and the owner writes them into the
     record. A later readiness or the apply refuses by a fixed gap when a discovered count differs.
     The attempt's `history` still keeps `affected_count`, and the result adds `replacements` (G.3).
   - **`retain` (B3).** A `retain` entry is a clear public path prefix that follows a declared host,
     port or scp colon: the host is still replaced, the prefix's bytes stay, and the rest of the
     span is still scanned. Readiness refuses a one-segment prefix, `/`, a prefix that contains a
     declared item, a prefix that matches the private-address pattern, and a prefix that never
     follows a declared item. It is public, so it needs no digest and no witness (G's source draft 8
     §1). Only readiness and the apply evaluate it; readers never need it. It carries no count: a
     count binds a declared item's occurrences so the apply can refuse drift, while a retained
     prefix is public text that stays. Readiness reports each prefix's occurrence total, by its
     index, for the owner's review (draft 9).
   - **Distinctness (G.2 (6)).** Markers and ID replacements are distinct and absent from every
     original; an undeclared span, port, path or context, or an untied protected path, refuses.

2. **Grammar and the occurrence model live in F's module, `repository/paradigm/peer_identity.py`
   (A13; B1, R7, R9).**
   - **One scan for every reader (R7).** Today `replacement_spans` (`:178-199`) scans hosts, then
     paths outside host spans, then numbers, and does not resolve a number that overlaps a host or
     path span, and `redact_line` (`:202-218`) applies its result. In landing 1 it becomes one
     left-to-right scan that takes the longest declared entry of the applicable form at each
     position and never rescans its output, so crossing entries give one result. Every reader moves
     to it in landing 1: the redaction verb, F's push check and the keyless verifier. The keyless
     span shape `_SPAN` (`:310-313`) widens to percent-encoded paths and `<path>!<n>` citations, so
     `alignment` pairs a marker over either.
   - **The occurrence model (B1), as data in F's module.** Occurrences are the results of the one
     scan over an object's bytes. Each result is attributed to exactly one entry, the longest
     declared entry at that position, so a span wins over its own host, port and path. The scanned
     bytes are commit messages, annotated tag messages and blob contents. A declared item in a tree
     entry name, or in any commit or tag header (`author`, `committer`, `tagger` and `mergetag`
     included; R6), refuses readiness, and nothing is renamed. A gitlink has no bytes to scan.
     Counts and witnesses both count these results, so they agree by construction.
   - **Pre-images (B1).** Every digest is the HMAC-SHA-256, under the record's key, of a
     domain-separated image:
     - `span`, `host` and `path` use F's images, through `marker()` (`:143-147`);
     - `port` is `ethos.rebuild.v1\0port\0<digits>`;
     - `id` is `ethos.rebuild.v1\0id\0<context name>\0<digits>`;
     - `trailer` is `ethos.rebuild.v1\0trailer\0<canonical key>: <value>`;
     - `paragraph` is `ethos.rebuild.v1\0paragraph\0<exact bytes>`;
     - an original's name is `ethos.rebuild.v1\0oid\0<oid>` (decision 1).

     `number()` keeps its own image for F's keyed numbers (`:150-164`).

   - The new span kinds and merge-request citations enter F's module as data, and ID entries name
     contexts from its named set (R9). A merge-request citation, its `!<n>` included, is one span.
   - `repository-paradigm`: MODIFIED "Peer identity markers are keyed, canonical and shared".
   - **Followed digests (R8).** The transform follows digests through `follow_digests`
     (`peer_identity.py:229-231`), as F's redaction does (`application/redaction.py:205-230`): a
     SHA-256 that a rebuilt blob holds for a file whose bytes the transform changed becomes that
     file's new SHA-256, round after round until none moves.
   - **Quoted original IDs (draft 10; closes A5's quotes and B2's path through them).** A bounded
     hex token of 7 to 40 characters in a commit message, a tag message or a blob, bounded by
     non-hex characters, that is a prefix of exactly one rewritten commit's or tag's ID is replaced
     by the rebuilt object's ID at the same length. A 64-character token is a content digest and is
     followed as the previous item says. Readiness counts quoted IDs per object by kind, never by
     value, and refuses a token that prefixes two or more rewritten objects; the apply refuses a
     quote of an object that the topological order has not rewritten yet. Archive evidence keeps
     resolving, and no original ID survives in the rebuilt history, signed or not.
   - **Marker pairing, the strict reading (decisions after draft 7, item 7; R8).** Under an
     effective record root, a rebuilt blob passes only when it equals its original with exactly the
     record's declared items replaced: spans by their markers, IDs in a declared context by F's
     numbers, followed digests (R8) and mapped IDs (draft 10). The check runs through the bijection
     while the originals are present. Any other difference, a changed word around a marker included,
     is judged as before. With the originals absent, this reader answers `unknown` (landing 2's
     decision 12). Landing 2 implements this reading; here `repository-paradigm` MODIFIED "Marker
     edits in record roots reproduce what they replace" only so that encoded paths and citations
     pair.
   - The `[openspec]` declaration of `rebuild.toml` modifies "OpenSpec carries the common rules",
     whose text is the paradigm contract's OpenSpec table (A22, verified in specs draft 1). Prewrite
     admission of the record modifies `assistant-projections` "Agent projections preserve native
     Change ownership" (review 4).
3. **Binding.** The record's blob must be the one at its path in `old` and in the rebuilt image;
   `base..old` touches only the authorizing Change; and the ref set is the blob's. Authorization is
   the record, and its expiry gates only a new apply. A recorded attempt still recovers.

### Readiness

4. **Readiness** is `lane repair-signature --rebuild <record> --key-stdin`, without `--apply`: the
   operation `lane.repair-signature.rebuild.preview` (decision 18; R1). Readiness and the apply are
   the only readers of the key.
   1. It checks the key's generation (decision 1).
   2. It walks the originals of every declared ref once, resolving each original that the record
      names by keyed digest (B2).
   3. It checks main against dev and every per-peer state through decision 6's listing, which lands
      in landing 1 (A16; R2).
   4. It computes the rebuilt image in memory with the transform engine, writing nothing; only
      readiness and the apply evaluate `retain`.
   5. It reports by count and fixed gap name: each entry's discovered count by the entry's index,
      each `retain` prefix's occurrence total by its index (draft 9), and the quoted IDs per object
      by kind, never by value (draft 10).

   It refuses:
   - **Discovered completeness (B7):** any discovered span the record neither declares nor retains.
     The discovered forms are: a host with or without a scheme and port; a path after a host or an
     scp colon; a module path's first element; an encoded path; a merge-request citation with its
     `!<n>`, as one span; an ID-context hit.
   - **Feed values (R5):** any occurrence of a value of F's local feed
     (`adapters/repo/peer_feed.py`), current or former, that no entry declares or retains. It admits
     a declared host outside the pattern when the feed protects it, so readiness refuses what F's
     push check would refuse at publication.
   - a declared item in a tree entry name or in any commit or tag header (B1; R6);
   - an entry whose `count` differs from its discovered count, a misplaced witness, a clear ID of an
     unsigned original (B2), an unknown or twice-named context (R9), or a refused `retain` prefix
     (B3);
   - an undeclared local ref, or a declared one in the wrong state;
   - a `keep` of an affected ref (R6), or of a ref that ETHOS cannot publish (B8);
   - a `retag` of a tag whose target is unaffected, or of a tag whose object targets another tag, by
     a fixed gap that names the ref and points to `retire` (draft 9; A5 of review 5);
   - a disposition other than `retire` for a ref outside `refs/heads/` and `refs/tags/` that the
     allowlist does not cover (A5 of review 5);
   - history that the walk cannot see: a shallow repository, `info/grafts`, or a linked worktree
     whose HEAD is detached or that holds a per-worktree ref, which `for-each-ref` in the main
     worktree does not list. Replace refs change nothing, since ETHOS runs Git with
     `GIT_NO_REPLACE_OBJECTS=1` (`adapters/repo/git.py:207, 268`) (A5 of review 5);
   - a quoted ID token that prefixes two or more rewritten objects (draft 10);
   - a `retag` without a valid `release.promote` record or a mapped maintenance base;
   - a transformed tag message that names a private address;
   - a `retag` whose original qualification cannot be verified: its tag policy is judged as the
     verified image of that qualification (landing 2's decision 13), never re-judged under today's
     CHANGELOG grammar, which 9 of aigw's 33 release tags predate (R30; AIGW blocker 1).

   It counts the peer's review refs, named as `_REVIEW_LISTINGS` names them (decision 6), that reach
   affected commits and are present locally, and reports the rest as unknown (A12, A20). It records
   nothing, not even an observed absence (landing 2's decision 14).

5. **ETHOS's own R8 (e) run is keyless readiness (R27).**
   - It is the operation `lane.repair-signature.census` (decision 18), one read-only mode that takes
     no record and no key.
   - Inputs: the local feed and F's grammar, as F's keyless preview uses them, plus the trailer
     rule.
   - Output: counts by form and ref class.
   - The counts and the disposition go in DR-0024, not in `tasks.md`.

### Peers

6. **Peer observation has one owner (B1 of review 1, R31 of review 2; R3).**
   - `observe_remote_refs` (`adapters/mutation/publication/observation.py:22-75`) extends its
     bounded run, parse and failure shape from exact refs to namespaces: `refs/heads/`, `refs/tags/`
     and `refs/ethos/`, plus, for counting, the review namespaces that `_REVIEW_LISTINGS` names
     (`adapters/mutation/publication/retirement.py:51-72`: `refs/pull/{}/head` and
     `refs/merge-requests/{}/head`).
   - In landing 1 it absorbs the namespace listing of proposal absorption
     (`adapters/mutation/publication/absorption.py:49-51`) and the push check's memoized
     advertisement (`adapters/admission/peer_identity_push.py:79-92`), which then read through it.
   - For a rebuild it refuses undeclared peer refs under `refs/heads/` and `refs/tags/` and any peer
     `refs/ethos/*`.
   - Its failure reports carry no stderr, for every caller; today they do (`observation.py:40`,
     `:43`, `:59`). `repository-governance`: MODIFIED "Remote publication observations preserve
     epistemic state". `command-plane`: MODIFIED "Result projection preserves diagnostic execution
     facts": a local tool or projection keeps its stderr, and a peer observation's failure carries
     its exact command, cwd and exit status without the remote's stderr, which can echo a private
     host or path (draft 9).
   - It returns states and records nothing; the commands with write authority record what it
     observes (landing 2's decision 14).

### Apply, verification, readers, release and rollback

Decisions 7 to 16 are landing 2's: the apply, tag messages, record resolution, verification, the
side store's attachment, the readers, maintenance releases and push baselines, observed absence,
`--release` and rollback. Their reviewed text, preserved at `ed3c367e2`, moves into landing 2's
Change (decision 17).

### Sequence and budget

17. **Two landings, two Changes (R6 of review 1).**
    - Landing 1 is this Change: record, grammar with the one scan for every reader (R7) and the
      named contexts (R9), binding, the transform engine without writes, the read-only peer listing
      through `observe_remote_refs` (R2, R3), the generation owner's read (R4), readiness with its
      publishability checks, and keyless readiness (`--census`). It is effect-free and releasable,
      and it ships in beta.9.
    - Landing 2 opens its own Change when its lane starts: the apply
      (`adapters/mutation/accepted/rebuild.py`; R36) with the generation in its attempt record (R4),
      verification, readers, the push-admission baselines and the strict marker pairing,
      `--release`, rollback and the pack steps (R10), as one candidate with two review and proof
      slices. It carries decisions 7 to 16, the former tasks 2.1 to 3.7 and the requirements of
      those parts from this Change's text at `ed3c367e2`.
    - One Change per landing keeps each Change's artifacts within the 500-line document ceiling, and
      this Change's archive adds exactly the requirements that landing 1 implements; each landing
      is a useful outcome on its own (PDC, Bounded Change Granularity).
    - Landing 1 is larger than the sizing's batch 1, because readiness needs the mapping and the
      release-policy reads, so it was re-estimated before its lane opened (R30).
18. **The `lane repair-signature` catalog entry (R1).** catalog-groups converted the command, and it
    is archived on dev at `fdb81a373`. Today its request requires `expect_head`
    (`contracts/operations/lane_repair.py:64-74`), and selection takes the first operation whose
    selectors match (`contracts/operations/declaration.py:223-256`). Landing 1's fields join that
    request, with their body in `ethos.application` (R16): the path `rebuild` and the switches
    `key_stdin` and `census`. `expect_head` becomes optional on the request, and each operation
    that takes it requires it. The entry gains `stdin="key_stdin"` and the redaction entry's
    limit, `stdin_limit=_KEY_CHARACTERS + 1` (`lane_repair.py:156-157`). Its operations, in
    selection order, with disjoint selectors before today's signature modes:
    - `lane.repair-signature.census`: selects `census=true`; takes nothing else; effects `read`;
      authorization none; not destructive.
    - `lane.repair-signature.rebuild.preview`: selects `census=false rebuild=set apply=false`;
      takes `key_stdin`; effects `read remote-read`; none; not destructive.
    - today's `lane.repair-signature.preview` and `lane.repair-signature.apply`, which select
      `census=false rebuild=unset`, keep their fields,
      `expect_head replacement corrections corrections_sha256 reason backup`, and require
      `expect_head`.

    A field outside the selected operation refuses `command_field_refused:<field>`, so `key_stdin`
    or any other field beside the census refuses. Readiness reads peers and declares `remote-read`;
    the census and today's signature modes read none and declare none. Landing 2 adds the
    switches `rollback` and `release` and the operations `rebuild.apply`, `rollback.preview`,
    `rollback.apply`, `release.preview` and `release.apply`, each before today's signature modes.

19. **Budget, in landing 1's lane (R26).**
    - DR-0020's product revisit happens there, since landing 1 alone may cross 78,000; its outcome
      is recorded in DR-0024's Evidence.
    - The test step is already taken: DR-0023 (`test-budget-step`) moved `python_tests` to 105,000
      for this Change and `source-budget-roles` together. DR-0010's Evidence holds DR-0019's
      revisit outcome and names landing 2's test removals, each with an expected size where
      landing 1 can measure one:
      - the bundle-based retag tests (`tests/unit/cli/land/publication/test_mapped_retag.py:61-97`);
      - fixtures repeated across the history-repair test modules.
    - Every figure names its commit and is measured at landing 1, after `go-own-root` and
      `beta-7-release` land; DR-0024's Evidence records them.
20. **DR-0024** records:
    - the side store's lifetime, including "originals held locally", never "purged" (A21), and the
      records' permanence (landing 2's decision 15);
    - the per-ref values and dispositions;
    - the record as the only authority, its key named only by F's generation, and its originals
      named in clear only when signed (B2);
    - the key's use, by readiness and the apply only (landing 2's decisions 8 and 10);
    - the two-landing sequence and landing 1's release, beta.9;
    - ETHOS's keyless R8 (e) counts;
    - DR-0020's revisit outcome (decision 19);
    - the out-of-scope list.

    DR-0024 stands until a later decision supersedes it. The spec deltas and DR-0024 validate before
    landing 1 (B3 of review 1).

## Risks / Trade-offs

- Every size is an estimate.
- **Scan:** about 48 s for aigw's blobs (inference); memoized.
- **Push check on an empty peer:** one whole-history scan per peer under `required` (A2).
- **Pack limits:** GitHub accepts packs up to 2 GiB with a 100 MiB per-file limit, while an
  adopter's GitLab refused a push over 20 MiB. ETHOS declares no limit: a peer's own size refusal at
  the real publication leads to the tag-stepped order, and the rehearsal records each step's pack
  size (R10; draft 9).
- **Quoted original IDs (A5 of review 5; draft 10):** every quote of a rewritten commit or tag is
  mapped to its image, so no original ID survives; an ambiguous quote refuses readiness.
- **The one scan changes a shared owner** that the redaction verb, F's push check and the keyless
  verifier call, in landing 1 (R7); task 1.5 holds their regressions.
- **Permanent records:** every rebuild's `rebuild:<id>` records stay in the attestation store for
  good (landing 2's decision 15).
- **The record stays in the rebuilt history** (decision 3), with its digests, counts, context names,
  witnesses, clear `retain` prefixes, and clear IDs of signed originals only (B2).
- **One key per repository:** the rebuild uses the repository's recorded key generation (R4).
- **Unproven:** aigw's off-dev commit count and blob sizes, and GitHub's push-event rule for tags;
  whether the adopters' original tags and commits that the record names are signed (review 5).

## Migration Plan

1. Landing 1 releases in beta.9.
2. Before `base`, the adopter lands every change the rebuilt history needs: its rehearsal peer
   declaration (R34), the fold of retired tags' CHANGELOG sections and any tool-source move off a
   retired Release (aigw: the rc-section fold and landing 2's observed absence), and any last
   release that the rebuild should include (aigw: 0.7.0, its 34th retag). Then it lands
   `rebuild.toml`, with each entry's count as readiness reports it, and runs readiness until it
   passes.
3. The steps after landing 2 releases, from the apply to turning CI on, are landing 2's Change's.

## Open Questions

None remain: draft 9's two questions are decided in `decisions-after-draft-9.md`.
