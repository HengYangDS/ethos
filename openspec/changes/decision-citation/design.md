# Design

## Context

See [proposal.md](proposal.md). `archive_readiness_gaps` materializes `openspec/**` of an exact tree,
archives the active Change there with the official OpenSpec CLI and validates the specifications;
the archive preview and proof planning call it. A decision record is a Markdown file named
`dr-<four-digit-id>-<topic>.md`, the paradigm's `documents.decision_record_name`, wherever a
repository keeps it, and `ethos.repository.registry.docs.decisions` already reads that name as the
`DR-####` identity. Records live outside `openspec/`, so the projection does not hold them.

## Goals / Non-Goals

**Goals:**

- A Change that a decision record names cannot archive until it cites the record.
- The check reads the same exact tree as the archive simulation.

**Non-Goals:**

- Judging whether the Change implements the decision. Citing the record puts it in front of the
  Change's author and reviewer, which the `repository-paradigm` Change lacked.
- A record that names a Change after the Change archived; it explains history.
- Names in prose. A record names a Change by its identifier in inline code, as the Docs Registry
  guide asks for identifiers.

## Decisions

- **Inline code names a Change.** A record names the active Change when an inline code span in its
  body is exactly the Change's name, as `` `repository-paradigm` `` does in DR-0013. ETHOS's nine
  records name Changes this way; their few bare mentions are task references in evidence or
  capability names in paths and prose, which a bare-word rule would misread.
- **The identity or the file name cites the record.** An artifact of the Change cites the record
  when it contains the `DR-####` identity as a word or the record's file name, for example in a
  link.
- **Read the records from the tree.** `git ls-tree` lists the tree's paths, and `git cat-file` reads
  each record whose name matches the grammar outside `openspec/`, which holds Change artifacts and
  their immutable archive, not records. The Change's artifacts come from the projection that the
  simulation already materializes. The check runs before the official CLI, and its gaps precede the
  simulation's.

## Risks / Trade-offs

- [The check refuses an adopter's archive on its first release] → On 2026-11-04 no governed
  repository had a decision record that names an active Change in inline code: 31 checkouts and 8
  lanes were read, among them di-effect's lane with 47 records and 8 active Changes. The check lands
  armed because it has no violation to remove.
- [An inline code span equal to a Change name means something else] → The Change cites the record
  once; a record rarely quotes an identifier equal to an active Change's name.
- [A repository keeps many records] → Each readiness check reads each record once; ETHOS keeps nine.
