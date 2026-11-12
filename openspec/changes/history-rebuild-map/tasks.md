# Tasks

## 1. Landing 1, in beta.9: record, grammar, readiness

- [ ] 1.1 Write the spec deltas (`repository-governance`, `repository-paradigm`, `command-plane`,
      `assistant-projections`) and DR-0024. Done when `openspec validate --strict` passes, a
      simulated archive leaves every main spec valid under `--specs --strict`, and DR-0024 passes
      ETHOS's own decision-record check, before any code lands.
- [x] 1.2 Re-estimate landing 1 and perform DR-0020's product revisit. Done when each figure is
      measured at landing 1 and names its commit, DR-0024's Evidence records the revisit outcome and
      cites DR-0023 for the test step, and DR-0010's Evidence lists landing 2's test removals, each
      with an expected size where landing 1 can measure one, and DR-0019's revisit outcome. The
      source budget measured product 77,745 and tests 99,942 at the lane base `d72001921`, and
      79,737 and 101,764 at `f420780e8`, the batch's two small Changes adding 30 and 43. `48aca1c1f`
      puts DR-0020's revisit outcome, a product step with removals first, in DR-0024's Evidence and
      cites DR-0023 for the test step. DR-0010's Evidence names the re-tag test, 33 test
      line-equivalents at `f420780e8`, and the repeated fixtures, which share no repeated four-line
      sequence at `48aca1c1f` and are measured when landing 2 removes them, with DR-0019's revisit
      outcome.
- [x] 1.3 Declare `rebuild.toml` in the paradigm's `[openspec]` table and admit it in prewrite. Done
      when prewrite admits the selected Change's `rebuild.toml` while its planning is partial and
      when it is complete, refuses another Change's `rebuild.toml`, and archiving the Change moves
      the record under the archive root. `95998d220` declares `change_record` in the `[openspec]`
      table and admits the record in prewrite. The five tests of
      `tests/unit/openspec/test_change_record_admission.py` cover partial and complete planning,
      refuse another Change's record and keep the archived copy immutable, and OpenSpec's archive of
      a copy of the lane's tree at `48aca1c1f` moved a probe record under the archive root.
- [x] 1.4 Parse and bind version 1 of the record. Done when each refusal fires by fixed gap:
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

  `95998d220` binds the record and `f420780e8` closes its review findings.
  `tests/unit/repository/test_rebuild_record.py` fires the free-string and ID-context gaps, and
  `tests/unit/adapters/repo/commit/rebuild/test_binding.py` fires the count, witness, generation,
  path, host, image, `retain`, unaffected-ref, unsigned, scope, ref-set, marker and public-peer gaps
  and admits a former Go module host only where an import path ties it. A witness whose object no
  declared old value reaches resolves to no message, so it refuses as misplaced too.

- [x] 1.5 Move F's grammar to the one scan and the occurrence model. Done when:
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

  `95998d220` moves the redaction, the push check and the keyless verifier to the one scan. The peer
  identity, occurrence, context and marker alignment tests under `tests/unit/repository/` cover the
  longest-entry scan, the scp colon, citations and encoded paths, today's redaction byte for byte,
  the stable named contexts with aigw's cache path and each kind's keyed pre-image;
  `test_originals.py` pins version 1's counts and witness indices over merges, roots, renames,
  shared blobs and a tag-only item.

- [x] 1.6 Extend `observe_remote_refs` to namespaces. Done when the rebuild's listing, proposal
      absorption's listing and the push check's advertisement read through it; the review namespaces
      come from `_REVIEW_LISTINGS`; each declared per-peer state is checked; undeclared peer refs
      under `refs/heads/` and `refs/tags/` and any peer `refs/ethos/*` refuse for a rebuild; no
      failure report of any caller carries the remote's stderr, while a local tool's or projection's
      failure keeps its own; and the listing records nothing. `95998d220` extends
      `observe_remote_refs` to namespaces.
      `tests/unit/cli/land/publication/test_namespace_listing.py` covers a listing that records
      nothing, a failed observation that keeps its boundary without the peer's stderr and absorption
      through the same observer; the readiness tests refuse an unread peer, a stray peer ref, a peer
      `refs/ethos/*` and a wrong per-peer state.
- [x] 1.7 Read the recorded key generation through one owner in `adapters/repo`. Done when it reads
      the last generation from `redaction:private-peer` records and `rebuild:<id>` attempt records,
      redaction calls it in place of `_require_generation`, and readiness refuses a key of another
      generation. `95998d220` adds `adapters/repo/key_generation.py`, which reads the last
      generation from both record kinds and which redaction and the binding call;
      `_require_generation` is gone from `src/`, `tests/unit/adapters/repo/test_key_generation.py`
      passes and the binding refuses a key of another generation with
      `rebuild_key_generation_mismatch`.
- [x] 1.8 Add the census and rebuild-preview operations to the `lane repair-signature` catalog
      entry. Done when `expect_head` is optional on the request and today's signature modes still
      require it, the entry reads `key_stdin` from standard input within the redaction entry's
      limit, `--census` selects `lane.repair-signature.census` first,
      `--rebuild <record> --key-stdin` selects `lane.repair-signature.rebuild.preview` without
      `--expect-head`, readiness declares `read remote-read` and the census `read`, and a field
      outside the selected operation refuses `command_field_refused:<field>`. `95998d220` adds both
      operations to the entry. `tests/unit/cli/test_lane_rebuild.py` covers each mode's operation
      and effects, `command_field_refused:<field>`, readiness and the census without a head while
      the signature modes need one, and readiness without `--key-stdin` reading no key.
- [x] 1.9 Add readiness and its keyless mode. Done when readiness counts peer review refs, reports
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

  `95998d220` adds readiness and the census, and `f420780e8` closes their review findings.
  `tests/unit/adapters/repo/commit/rebuild/test_readiness.py` reports by count and index, writes
  nothing and fires a case of each refusal above by its fixed gap, the quoted-token refusal in
  `test_discovery.py`; `test_census.py` counts by form and ref class and leaves a feed the clone
  cannot know `unknown`.

- [x] 1.10 Run ETHOS's keyless readiness (`--census`, R8 (e)). Done when its counts by form and ref
      class and its disposition are in DR-0024. The census at `d72001921` walked 62 local refs,
      13,328 commits and 42,500 blobs in 2,132 s and left no ref unwalked; DR-0024 (`48aca1c1f`)
      records its counts by form and ref class and the disposition that ETHOS's own history is not
      rebuilt in 0.2.0.

## 2. Acceptance

- [ ] 2.1 Pass the precheck, the impacted sweep and readiness at this landing's head, and run
      `ethos lane repair-signature --census` on ETHOS's own head. Done when each passes on the
      committed head and the census reports its counts without a gap.
