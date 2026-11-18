---
subject: ethos:decision:decision-record-form
role: decision
state: canonical
decision_id: DR-0031
decision_status: accepted
date: 2026-11-18
relations:
  current_owner: ../governance/docs-registry.md
  updates:
    - DR-0011
    - DR-0026
---

# DR-0031: Decision Records Have One Form, and a Record Is Kept and Marked

Purpose: preserve why every governed repository writes its decision records in one exact form,
why a record that no longer governs stays in its directory and says so, and where the form
follows the common standard for such records and where it does not.

See also: the [Docs Registry](../governance/docs-registry.md#decision-records), which owns the
form; [DR-0011: Documentation portability](dr-0011-documentation-portability.md), whose freedom of
physical shape this record ends for the decisions directory; and [DR-0026: The 0.2.0 release
candidate gate](dr-0026-release-candidate-gate.md), whose sentence on edits after acceptance this
record replaces with a rule.

## Context

On 2026-11-18 the owner asked whether a superseded record is deleted or kept with a status, and
why the numbers of ETHOS's records are not contiguous. The answers showed no single practice.

- The accepted requirement kept a record only while deleting it would lose a reason. ETHOS had
  removed seven records in one commit of 2026-08-15 and none since, while four later records
  replaced parts of older ones in four different words, and no older record named its successor.
- Fourteen governed repositories were read at their accepted branches. Five passed the product's
  check of decision records and still differed in the relation that names the current owner, in
  the subject's form, in where the date is written (four carriers and one repository with none),
  in further keys, in the preamble, in the index and in what else the directory holds. Their
  indexes stated four different rules for a record that no longer governs. Two more
  repositories held older forms with other names, two series and lifecycle directories. Seven
  held no record.
- A committee of five seats first proposed, twice and unanimously, to keep in the tree only
  records in force and to give every removed number an index row. It followed the accepted
  requirement. The owner rejected removal in these words: 「DR 那里删除这个建议我觉得不妥。为何不是退役标识？」,
  and set the end state: one strict form in every repository, all that can be unified is
  unified, following the norms and standards.

## Decision

1. **Kept and marked.** An accepted record never leaves its directory. When it no longer
   governs, its status says so in the front matter, it names its successor where one exists,
   and a banner under its title and under each of its section headings says it to a reader who
   lands on any passage.
2. **One form.** The same directory, file name, front-matter keys in the same order, date,
   current-owner relation, banner, five sections and index table in every governed repository.
   The Docs Registry owns the exact form; this record owns the reasons.
3. **The standard's words.** The form follows the architecture decision record as its common
   template writes it: the directory, one numbered record for each decision, numbers never used
   twice, a status and a date in the front matter, an old record kept and marked. The statuses
   are accepted, superseded, deprecated and rejected.
4. **A changed ruling is a new record.** A record is fixed at acceptance. A later record either
   supersedes it whole and can be used alone, or updates a named part and cannot. The test is
   asked of the old record: does it still say something in force that the new one does not
   carry?
5. **A chain has one link.** A sentence or a list item is updated once. Its next change is a
   record that restates and supersedes.
6. **Every number is a row.** The index is one table with a row for each number, written in the
   end by the product from the records.
7. **What was removed comes back.** A record that was once accepted and later removed returns
   as it last was, marked.

## Alternatives Rejected

- **Only records in force stay in the tree; Git and an index row hold the rest:** the first
  committee's proposal. Rejected by the owner. Its reason was that a search by meaning returns
  old text beside new; the banner under every heading and the mark at an updated passage answer
  that without hiding what was decided.
- **Each repository keeps its own form under shared metadata, as DR-0011 allowed:** rejected
  because the reading of the fleet showed what it produces: nine differences among five
  repositories that pass the same check.
- **The standard's template taken whole, with its key names and its sections:** rejected because
  every released engine requires the fleet's status key, the name grammar is an accepted
  requirement, and the five sections are already checked. The form takes the standard's
  directory, statuses, date and practice, and states each place where it departs.
- **A status for a proposal:** rejected because a record enters the tree decided. OpenSpec holds
  proposals.
- **Lifecycle directories, one for each status:** rejected because a status then lives in a path,
  a move breaks every link, and three of the older trees show the result.
- **Editing a record when its ruling changes:** rejected because a reader of a cited number can
  no longer tell what was decided when. Two repositories had made it their rule.

## Consequences and Boundary

- The form departs from the standard in the status key's name, the file name's prefix, the
  section headings, five keys of the fleet's document metadata, a relation for a record that
  replaces a part, and in having no status for a proposal and no list of persons. The Docs
  Registry states each beside the standard.
- The accepted requirement on decision records changes: a record is kept, and the decisions
  directory is no longer a shape that a repository may choose.
- Old text stays in every tree. What keeps a reader from taking it as current is the banner,
  the marks and the index, not its absence.
- Until an engine accepts the four statuses, a repository does everything that leaves a
  status alone. A record that is superseded, deprecated or rejected, and a record that comes
  back, takes its status, relation and banner together once its engine accepts them. So no
  file ever contradicts itself.
- This record adds no check. The checks follow in the law's stages: a report first, then
  refusal after a clean census; a Change that removes a record is refused in that last stage.
- Each repository's keeper migrates it through its own lane in two steps: what today's engines
  accept by the frozen beta, the statuses with the engine that reads them.

## Evidence and Revisit

- The owner's words of 2026-11-18 and 2026-11-19, first-hand: the question; the direction to a
  committee; the rejection of removal; strong consistency under the norms; the delegation of
  the remaining questions to the release lead; and that this text lands during the freeze,
  since it refuses nothing.
- A census of fourteen governed repositories at their accepted branches, 109 numbered records,
  laid side by side against one form.
- Eight outside practices read at their sources, each of which keeps an old record and marks it.
- Three committee rounds of five seats: two on the form that removed, one on this form, whose
  twenty changes are held in it.
- Trials on the released engine: the keys and marks of the first step pass; any status but
  accepted is refused.

Revisit when the reports count many updates on single records, which would mean that parts are
updated where rulings should be restated; when the common template changes its front matter;
and when a repository states a need that the form does not meet.
