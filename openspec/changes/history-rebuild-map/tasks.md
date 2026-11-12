# Tasks

## 1. Landing 1, in beta.9: record, grammar, readiness

- [ ] 1.1 Write the spec deltas (`repository-governance`, `repository-paradigm`, `command-plane`,
      `assistant-projections`) and DR-0024. Done when `openspec validate --strict` passes, a
      simulated archive leaves every main spec valid under `--specs --strict`, and DR-0024 passes
      ETHOS's own decision-record check, before any code lands.
- [ ] 1.2 Re-estimate landing 1 and perform DR-0020's product revisit. Done when each figure is
      measured at landing 1 and names its commit, DR-0024's Evidence records the revisit outcome and
      cites DR-0023 for the test step, and DR-0010's Evidence lists landing 2's test removals with
      their expected sizes and DR-0019's revisit outcome.
- [ ] 1.3 Declare `rebuild.toml` in the paradigm's `[openspec]` table and admit it in prewrite. Done
      when prewrite admits the selected Change's `rebuild.toml` while its planning is partial and
      when it is complete, refuses another Change's `rebuild.toml`, and archiving the Change moves
      the record under the archive root.
- [ ] 1.4 Parse and bind version 1 of the record. Done when each refusal fires by fixed gap:
  - a free string;
  - a host outside the pattern, while a former Go module host tied as an import path's first element
    and a host that the local feed protects are admitted;
  - a one-segment path;
  - an untied protected path;
  - a declared path whose digest equals the public path's or one of its segment-boundary prefixes',
    or an unresolvable public-distribution peer;
  - a key whose generation differs from the record's or from the repository's last recorded one;
  - a marker in an original;
  - an ID without a context, or with an unknown or twice-named context;
  - a misplaced witness: its object reached by no declared old value, or its result's HMAC under the
    key unequal to its entry's digest;
  - a clear ID of an original that carries no signature that today's trust anchor verifies;
  - an entry whose `count` differs from the discovered count;
  - a `retain` prefix of one segment or `/`, one that contains a declared item, one that matches the
    private-address pattern, or one that never follows a declared item;
  - `base..old` outside the Change, a record blob changed in the image, or a ref set other than the
    blob's;
  - a `rebuild` or `retag` reaching no affected object (`retire` is admitted for any ref).
- [ ] 1.5 Move F's grammar to the one scan and the occurrence model. Done when:
  - the redaction verb, F's push check and the keyless verifier all use the one left-to-right scan,
    and their regressions pass, each named context pattern matching as before;
  - `_SPAN` admits a percent-encoded path and a `<path>!<n>` citation, and `alignment` pairs a
    marker over either;
  - `_CONTEXTS` patterns carry stable names, and aigw's cache-path context joins the set as data
    with its own test;
  - one occurrence gives one result, crossing entries one result, a span wins over its own host,
    port and path, an scp colon is kept, a citation is replaced as one span with its number, and
    digits inside a hex digest stay;
  - counts and witnesses agree over a merge commit, a root commit and a renamed path, a blob
    reachable at two paths counts once, and an item only in a tag message is witnessed by the tag;
  - each entry kind's digest is the keyed HMAC of its own pre-image;
  - a fixture pins version 1's counts and witness indices, so a later change to the occurrence rules
    fails it.
- [ ] 1.6 Extend `observe_remote_refs` to namespaces. Done when the rebuild's listing, proposal
      absorption's listing and the push check's advertisement read through it; the review namespaces
      come from `_REVIEW_LISTINGS`; each declared per-peer state is checked; undeclared peer refs
      under `refs/heads/` and `refs/tags/` and any peer `refs/ethos/*` refuse for a rebuild; no
      failure report of any caller carries the remote's stderr, while a local tool's or projection's
      failure keeps its own; and the listing records nothing.
- [ ] 1.7 Read the recorded key generation through one owner in `adapters/repo`. Done when it reads
      the last generation from `redaction:private-peer` records and `rebuild:<id>` attempt records,
      redaction calls it in place of `_require_generation`, and readiness refuses a key of another
      generation.
- [ ] 1.8 Add the census and rebuild-preview operations to the `lane repair-signature` catalog
      entry. Done when `expect_head` is optional on the request and today's signature modes still
      require it, the entry reads `key_stdin` from standard input within the redaction entry's
      limit, `--census` selects `lane.repair-signature.census` first,
      `--rebuild <record> --key-stdin` selects `lane.repair-signature.rebuild.preview` without
      `--expect-head`, readiness declares `read remote-read` and the census `read`, and a field
      outside the selected operation refuses `command_field_refused:<field>`.
- [ ] 1.9 Add readiness and its keyless mode. Done when readiness counts peer review refs, reports
      each entry's discovered count and each `retain` prefix's occurrence total by index, counts
      quoted IDs per object by kind, never by value, keeps a retained prefix's bytes while replacing
      the host before it, resolves keyed-named originals, records nothing and outputs none of the
      fixture's exact literals; `--census` reports counts by form and ref class; and readiness
      refuses:
  - an undeclared span, or a local feed value, current or former, that no entry covers;
  - a declared host followed by an undeclared port or path;
  - an undeclared ID context;
  - a declared item in any commit or tag header, `tagger` and `mergetag` included, or in a tree
    entry name;
  - an undeclared local ref, or a wrong per-peer state;
  - main other than dev;
  - a `keep` of an affected ref, including a tag whose own message holds a declared item, or of a
    ref that ETHOS cannot publish;
  - a `retag` of a tag whose target is unaffected, or of a tag whose object targets another tag, by
    a fixed gap that names the ref and points to `retire`;
  - a disposition other than `retire` for a ref outside `refs/heads/` and `refs/tags/`, such as
    `refs/notes/*`, `refs/replace/*`, `refs/stash` or `refs/prefetch/*`;
  - a shallow repository, `info/grafts`, or a linked worktree whose HEAD is detached or that holds a
    per-worktree ref;
  - a quoted ID token that prefixes two or more rewritten objects;
  - a `retag` without a `release.promote` record or a mapped maintenance base;
  - a transformed tag message naming a private address;
  - a `retag` whose original qualification cannot be verified.
- [ ] 1.10 Run ETHOS's keyless readiness (`--census`, R8 (e)). Done when its counts by form and ref
      class and its disposition are in DR-0024.

## 2. Landing 2, slice A: side store, apply, verification, hook, retag

- [ ] 2.1 Create the side store and the apply's preconditions, and add the rebuild apply operation.
      Done when:
  - the store is owner-only, has no alternates either way and holds each old value under its own
    ref, built from the restore that `_verify_backup_recovery` now keeps;
  - the bundle lists every declared old value and release-named commit and the restore `fsck`s each;
  - the local allowlist admits remote `HEAD` symrefs;
  - the apply refuses each precondition by name, and a key of another generation, a witness that
    fails under the key, an unresolved keyed-named original or a differing count refuses before any
    record or side store exists;
  - the attempt record carries the key's generation and every keyed-named original's clear ID, and a
    later redaction with a key of another generation refuses `redaction_key_generation_changed`;
  - `lane.repair-signature.rebuild.apply` is destructive under `authorize`, with no
    `confirm-irreversible`;
  - recovery passes.
- [ ] 2.2 Rewrite, prove, then move. Done when:
  - every rebuilt commit keeps its dates, authors, committers and parent order byte for byte, and a
    declared closing paragraph leaves its message;
  - a digest of a changed file follows it;
  - each `retag` target's transformed tag message, with no SSH, OpenPGP or X.509 signature armor, is
    in the signed result record;
  - G.5 (5) passes on the rebuilt objects, the kept refs and those messages before the ref
    transaction;
  - every ref is connected in the main store alone;
  - an off-dev annotated tag and an off-dev maintenance tag are held under `rebuilt/`;
  - a lightweight tag retires;
  - a binary blob or a reparsed TOML, YAML or JSON with other keys refuses;
  - one Go string gets one replacement;
  - no Git argument carries a literal, and failure reports hold no stdout or stderr.
- [ ] 2.3 Add the resolution and verification owners and the cache. Done when verification reads no
      key and checks the record blob binding, the signed attempt and result records, the structural
      bijection and the keyless private-address scan, and resolves keyed-named originals through the
      attempt record; verification, a retag preview, a retag apply, a publication and replayed hook
      admission pass after `reflog expire --expire=now --all` and `gc --prune=now`; a gained
      `objects/info/alternates` refuses; an emptied side store makes every reader that asks for a
      rebuild edge, `attested_archive_transition` included, answer `unknown`; and a cache hit skips
      signature verification only.
- [ ] 2.4 Retire retag's bundle restore. Done when `_restore_original` and `_bound_backup` are gone,
      and `land --retag` reads the prepared message from the result record through the
      record-resolution owner without the key, keeps the tagger, writes nothing while attached, and
      checks G.5 (5) and its release-tag policy on each new tag.
- [ ] 2.5 Read historical source and the hook through the owners. Done when an unplanned
      `refs/ethos/rebuild/` update refuses and the historical-source reader admits the record's
      refs.
- [ ] 2.6 Add rollback and its two operations. Done when, after gc and after `land --retag`,
      `--rollback` restores every declared old value and reverses each retag plan inside one
      recorded intent; its preview runs without `--expect-head`, refuses by fixed gap a declared ref
      away from its recorded rebuilt value, and blocks by fixed gap, naming the ref and the peer, a
      peer whose state differs from the record's declared state; and its apply is destructive under
      `authorize`.

- [ ] 2.7 Map quoted original IDs in the apply. Done when every bounded 7- to 40-hex token in a
      commit message, a tag message or a blob that prefixes exactly one rewritten commit's or tag's
      ID becomes the rebuilt object's ID at the same length; a 64-hex token follows the digests; a
      quote of an object that the topological order has not rewritten yet refuses; the apply maps
      exactly the quotes that landing 1's readiness counted, per object and kind; archive evidence
      still resolves; and no original ID, signed or not, remains in the rebuilt history.

## 3. Landing 2, slice B: readers, publication, release

- [ ] 3.1 Read the rebuild edge in release, through `release_tag_policy` and `release_ref_subject`,
      and in publication, conservation and archive provenance, and set the push baselines. Done when
      a re-created tag whose CHANGELOG uses an older grammar publishes on its original
      qualification; a re-created tag on an older commit and a maintenance tag whose range archives
      a Change holding a declared span publish, also after `gc --prune=now`, without re-judging the
      rebuilt commits; publishing the rebuilt dev and main into an empty peer re-judges no rebuilt
      commit while a commit beyond the verified image of a branch's declared old value is judged as
      in any push; and a re-created tag pushed before any branch that reaches it re-judges nothing
      at or below the verified image of its original target.
- [ ] 3.2 Record observed absence and fold it. Done when `ethos publish` (apply) records the first
      observed absence of a declared retired tag on a re-created peer, and, after retiring a tag,
      re-creating both bare peers, publishing, `reflog expire` and `gc --prune=now`, a set update
      still ends members.
- [ ] 3.3 Add `--release`, its two operations and the `rebuild:<id>` lifetime key. Done when
      `--release` previews without `--apply` or `--expect-head`; its apply with
      `--apply --authorize --expect-head <rebuilt dev>` records each absence it observes that
      publication did not, refuses before every due receipt (only where a peer held a ref ETHOS
      publishes; none for `candidate/dev`) and every absence, then deletes only `rebuilt/` refs
      under its lock; a second run is `already_applied`; the apply is destructive under `authorize`;
      and every `rebuild:<id>` record survives gc and the side store's deletion and is never planned
      by `hook retire-records`.
- [ ] 3.4 Publish to two bare peers and a declared rehearsal peer. Done when rebuilt branches,
      re-created tags and kept refs publish into a ref-less peer by creation, branches before tags,
      with the re-created tags that no published branch reaches oldest first; when a bare peer that
      refuses large pushes refuses a branch's push and the publication owner classifies it by its
      fixed forge patterns as `publication_pack_refused:<peer>`, with the recorded step sizes and no
      byte of stderr, the plan's next step sends that branch's reachable re-created tags oldest
      first, then the branch; the rehearsal records each step's pack size and a refused step is
      named by it; an unmatched push failure keeps its fixed gap without stderr; ETHOS declares no
      pack limit; a peer keeping originals refuses `release_tag_immutable` by name; a hooked
      `push --mirror` refuses; `refs/ethos/attestations-set` is neither rewritten nor published; and
      no peer receives an object holding a declared item.
- [ ] 3.5 Prove a rebuilt head and land a new Change after the side store is deleted. Done when the
      archived-intent reader refuses `unknown` instead of admitting a proof without its commitment.
- [ ] 3.6 Read a rebuilt record-root blob through the bijection in marker pairing. Done when a
      rebuilt blob under a record root that equals its original with exactly the declared items
      replaced passes, with spans replaced by their markers, an ID in a declared context replaced by
      its keyed number, a followed digest and a mapped ID; a changed word around a marker is judged
      as before and refuses `record_marker_unpaired`; and with the originals absent the check
      answers `unknown`.
- [ ] 3.7 Refuse publishing a declared `retag` ref before its re-created tag exists. Done when the
      rebuild's publication admission refuses a declared `retag` ref whose current value equals its
      recorded old value, by a fixed gap that names the ref, in both F's push-check modes, and
      admits the ref once `land --retag` has recorded the re-created tag.

## 4. Acceptance

- [ ] 4.1 Pass the precheck and the impacted sweep at each landing's head, and run
      `ethos lane repair-signature --census` on ETHOS's own head. Done when both pass on the
      committed head and the census reports its counts without a gap.
