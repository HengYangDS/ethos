# Design

## Context

See the [proposal](proposal.md). The pin module holds each release's class as data
(`release_class`), and three adapters read the consumers that the host store's installations
record (`grep -rln installation_consumers src`). A release's predecessors reach the hosted journey
through one dispatch input, `journey_previous`, which a person fills
(`grep -n journey_previous .config/ci/pipeline.cue`). The release table of the release binding has
one reader of its key set, the paradigm's `release_binding_gaps` (`grep -rn RELEASE_KEYS src`),
which reports every key but `mirror`.

The product's changelog lists 40 released entries at the base: 11 of class `attested-main` and 29
of class `checksum` (`released_versions` over `CHANGELOG.md`, classed by `release_class`).

The archived `rc-plan` design, appendix B.3, names the parts of this row: the subject set, the
window, the classes, the carrier `[release] upgrade_from`, the operation that derives it in the
release lane, its re-derivation at the release tag, and a reading in `status` for a subject
outside the window. Its B.8 lists the Change as the set, the window, the classes, the carrier and
the operation.

## Goals / Non-Goals

Goals:

- One definition of the subject set and of the support window, as a reading of trees.
- A record of what a release upgrades from that names releases and classes only.
- An offline operation that derives the record for the release lane and shows its evidence.
- A decision record for the candidate's subject set and its one waiver, DR-0030.

Non-Goals:

- The refusal at the release tag and the reading in `status`. The drafts
  `release-predecessors-binding` and `upgrade-path-status` hold them.
- A writer of the record. The release lane records what the operation derives.
- The journey reading the record in place of its dispatch input. The journey module is rewritten
  by another Change of the same batch, and the rehearsal row renders from the record.
- A rule for a governed repository, and a declaration that a subject makes about itself.
- The restore-then-rollback journey per predecessor, which belongs to a later row.

## Decisions

1. **The subject set is a reading, defined in one pure module.**
   - **Rests on:** the owner's decision of 2026-11-15, which the proposal and DR-0030 state;
     DR-0029's condition for the candidate.
   - **Considered:** a number in the gate's record, which was wrong in both directions within a
     day; a list of subjects in the release binding, which names repositories in tracked text.
   - **Chosen because:** a reading cannot go stale and names nothing. The cost is that the set
     exists only on a host that can read the trees.
   - **Applies to:** `ethos.repository.release.predecessors`, which every later reader of the set
     imports. It does not count subjects for the weekly page; the page counts the operation's rows.
2. **The subjects are the consumers that the host store records, less the releasing repository.**
   - **Rests on:** `installation_consumers`, which already has three readers; appendix B.3, which
     names this source, and its B.9, which leaves the source open.
   - **Considered:** a scan root given as an argument, as the retirement of host supply takes,
     which puts a path in the command line and reads repositories that never selected a runtime;
     a tracked list, which names repositories.
   - **Chosen because:** it needs no argument and reads exactly the repositories that selected an
     installed release on this host. The trade-off is that a repository on a build of its own
     source, one known only through an installation pinned before consumers were recorded, or
     one that exists only on a forge, is not read.
   - **Applies to:** `read_subjects`. A record that cannot be read, a repository that is gone and
     one whose pin's history cannot be read are counted as unread and refuse nothing: the owner's
     definition counts what the host can read, which supersedes B.3's refusal of an absent
     consumer. Each record that cannot be read counts once. A repository whose accepted
     branch or tree cannot be read is unread, never a subject without a pin. An installation
     that records no consumer names no repository, so it is counted by itself and the result
     states what it did not read. The first read on the releasing host's real trees, a lane
     task, checks what is not read.
3. **A recorded consumer is a subject by its selection; a pin, where declared, also names it.**
   - **Rests on:** the release lead's ruling of 2026-11-15 and the fleet reader's reading by form
     that DR-0030 carries: part of the readable trees declare no pin and none the bare form.
     Appendix B.3 takes the releases that the accepted pin and `CURRENT` name. A consumer record
     is one line, the consumer's path (`record_consumer` in the host store module), and a
     repository records itself in each installation it selects or holds as rollback supply (the
     host retention module's own description). On the preparing host every recorded consumer was
     under two installations of two releases (a read-only count of 2026-11-15). For a declared
     pin that cannot be read: the release lead's ruling of 2026-11-16, and DR-0030, by which a
     repository takes the release with or without a tracked pin.
   - **Considered:** requiring a pin, as first built, which drops every subject without one; the
     release of the installation that records the consumer, which the record cannot name while
     one consumer is under two installations, and a guess of the newer one is wrong after a
     receipted departure back; a second reader of `CURRENT`; counting a consumer whose declared
     pin cannot be read as unread, which drops a subject for a declaration that changes no
     selection.
   - **Chosen because:** the selection is the runtime that a release upgrades, and the reader
     that every transition uses already validates it. A pin names the release that a fresh
     clone installs, so both contribute, and the result shows both. A declaration that cannot
     be read does not change which runtime a repository selects, so the subject stays and the
     pin is counted by itself.
   - **Applies to:** every recorded consumer. One with neither a readable pin nor a readable
     selection is counted as unread. A declared pin that cannot be read (two keys, a version
     prefix, text that is not TOML) names no release and dates no bump: its repository is a
     subject by its selection, inside the window, and the result counts such pins by themselves,
     apart from the unread consumers. A failed Git read is no unreadable pin: only the
     declaration's text is judged. A selection that cannot be read, such as a selector that
     is torn or names an invalid generation, is the same case from the other side: it names
     no release, its repository stays a subject by its pin, and the result counts such
     selections by themselves. Only a repository without a selector has no selection. A
     subject frozen on its runtime is not known to the
     derivation: its release stays a predecessor while it is inside the window. Its waiver is
     DR-0030's, and no field that the product reads.
4. **A subject is inside the window while its last bump is at most 14 days before the newest.**
   - **Rests on:** the committee's words for this row, "the support window measured from the last
     landed bump", as the release lead ruled on 2026-11-15; appendix B.3, which proposes two
     weekly periods.
   - **Considered:** classing a subject by the age of the release it pins, which appendix B.3's
     "older adopter" suggests. The two readings differ in one case, a subject that bumps to an
     old release: by its bump it is inside and its release is a predecessor; by its release's
     age it is outside. That reading also compares a date written in the changelog with a
     commit's time. Also considered: a window from the release's tag date, which lets the frozen
     beta fall out of its own soak when a week slips.
   - **Chosen because:** the newest bump is always inside its own window, so time alone moves no
     subject, and the reading needs Git facts only. The trade-off: a subject that bumps to an
     old release keeps that release among the predecessors.
   - **Applies to:** `supported`. A subject whose bump has no time is inside the window. The
     72-hour count of the candidate is not computed here.
5. **A bump's time is the time of the accepted commit that changed the pinned release.**
   - **Rests on:** one pickaxe search of the accepted branch's history over the Mise
     configuration, whose pattern bounds the release's name on both sides. The search counts
     occurrences, so a change of form that keeps the release is not found (observed with Git
     2.56.1; no regression covers it).
   - **Considered:** the accepted head's time, which any commit moves; the time of the accepted
     closeout's Attestation, which is the exact landing time and needs each subject's
     Attestation set read and verified.
   - **Chosen because:** it is one Git read per subject and needs no other repository's
     Attestations. The trade-off: the commit was made in its lane before it landed, so a clock
     read from this time starts early by the lane's duration.
   - **Applies to:** `_subject`. A change of form that keeps the release is no bump. A subject
     without a pin has no bump to read, and its consumer record holds no time: the record is
     the path alone, and the record file's own time is the time of its first writing under one
     installation, which a restore changes. Such a subject is inside the window, and the result
     gives its time as unknown.
6. **The record is the table `[release.upgrade_from]`: one release per key, its class as value.**
   - **Rests on:** appendix B.3, which gives the carrier its place and forbids subjects in it;
     the pin module's classes.
   - **Considered:** an array of entries that also carry each subject's accepted head, which
     shows a count of subjects and identifies them; a file of its own, which adds a carrier to
     the binding layer.
   - **Chosen because:** several subjects on one release are one row, so the table holds no count
     of them, and TOML refuses a release named twice. A class other than the one the pin module
     gives that release is refused, so the record cannot disagree with the data.
   - **Applies to:** `recorded`, and the paradigm's key set, which now admits `upgrade_from`. A
     recorded release that no subject names is allowed: the lane may add one. The paradigm
     reads a declared record through `recorded` and reports one that it refuses under
     `release-binding`, at the carrier that the key had while no reader consulted it, so the
     paradigm and the read cannot disagree and no tree that passed the previous release is
     refused. The paradigm's repair never deletes a record.
7. **One read-only operation, `ethos lane upgrade-from`, derives and compares.**
   - **Rests on:** appendix B.3, which asks for a catalog operation in the release lane with each
     subject's accepted head and pin as evidence.
   - **Considered:** an apply mode that writes the table, which needs an admitted carrier edit
     and its preview; a field of the release preview, which shows the set only once a tag is
     asked for.
   - **Chosen because:** the read is the smaller half and the one the other parts reuse. The lane
     writes one file by hand per release of the product, and none per bump of a subject.
   - **Applies to:** the committed head of the lane. It exits 0 on every verdict, as a read does,
     and its rows are ordered by bump. Subjects that no bump dates come last, in the order in
     which their records are read, and no path is printed. For the subjects inside the window its
     result counts those with a pin by form and those by selection alone, among the latter the
     subjects whose declared pin cannot be read, the unread consumers, and for the release
     itself and each predecessor the subjects that name it by pin and by selection alone. The
     weekly page's measure of pins in reads both numbers there: the total is the sum of the
     three counts, less the waived repository under DR-0030, and the pins in are the subjects
     whose pin names the release. A subject whose declared pin cannot be read is in the total
     once, under selection alone, and is no pin in. A refusal carries the gaps of its cause:
     the record's three gaps name the record as their registered repair, an operating system
     error is `release_upgrade_from_store_unreadable` with the error's name and no path, and
     any other gap names its own repair or a general instruction. A record that its reader
     refuses is no record, and the derivation goes on, so the refusal carries the derived
     releases with their classes: its repair asks for exactly those. A refusal always blocks,
     also one that carries no gap, which is then named by its class. An installation
     directory that is a link is read as the directory it names, once, also when its
     target is listed beside it; a link whose target is gone is counted with those that
     record no consumer. Reading fewer subjects would ask a release for fewer
     predecessors. The retirement of unused installations never deletes through a link,
     which is a rule for a removal.
8. **A version that the changelog does not list is counted and named, and refuses nothing.**
   - **Rests on:** the release lead's ruling of 2026-11-15; the owner's definition, which counts
     what the host can read.
   - **Considered:** refusing the derivation, as appendix B.3 does and as first built, which
     lets one tree on a development build stop the read for every other tree; asking the forge,
     which the operation cannot do offline.
   - **Chosen because:** offline, the changelog is the list of releases, and a development build
     goes by its distribution version, which no entry lists. The result names such a version
     with its count, so it is seen and stops nothing. This replaces B.3's refusal, as for the
     absent consumer.
   - **Applies to:** `derive`, `named_by` and the result's unlisted versions. The releasing
     repository's own version without a changelog entry still refuses, and so does a changelog
     whose history is out of order or names a release twice, with the history's own errors:
     the previous release is read from that order. A changelog entry does
     not prove a publication; the journey still asks the forge for each predecessor.
9. **The subject set and the waiver are a decision record of this Change, DR-0030.**
   - **Rests on:** DR-0029, which requires that a later waiver is a successor record that names
     it; the owner decided the set and the waiver on 2026-11-15.
   - **Considered:** a line of the release entry, which is no record; a field of the release
     binding, which needs a reader and puts a subject's shape into configuration.
   - **Chosen because:** the gate's own record asks for it, and a record keeps the alternatives
     and the revisit condition across the Changes that read the set.
   - **Applies to:** `docs/decisions/dr-0030-candidate-subject-set.md` and its index entry. The
     record names no repository, fixes no number of subjects and adds no checker. The owner
     reads its text before this row lands.

## Risks / Trade-offs

- The measured size is 234.4 product and 297.9 test line-equivalents, and no tools change, against
  a plan of 140, 120 and -30 (`measure_budget.py` on the base). The set, classes and carrier take
  81.1 and 99.8; the operation takes 153.3 and 198.1. The plan's removal in tools is the journey's
  reader, which this Change does not touch.
- Until the draft `release-predecessors-binding` lands, a release can be tagged with an empty or
  incomplete record, and only the read shows it.
- An engine older than this Change reports the table as an unread key, and its repair deletes it.
  The product's own binding therefore records the table only in a lane whose selected runtime
  contains this Change.
- The subjects are those of one host. A release cut on another host derives another set.
- A bump's time precedes its landing by the time its lane took, so a clock read from it starts
  early by that much.
- A subject's selection is validated as every transition validates it, so the operation's time
  grows with the count of recorded consumers. It is not measured on real trees.
- A subject without a readable pin is always inside the window, so a repository that stopped taking
  releases and keeps an old selection stays a subject until its record leaves the host store.
- The operation count in the catalog test is a number kept by hand, which every Change that adds
  an operation edits.
