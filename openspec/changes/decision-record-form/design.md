# Design

## Context

The form was written by the release lead with a committee of five seats in three rounds. The
first two rounds proposed to keep in the tree only records in force. The owner rejected removal
and set the end state: one strict form, kept and marked, under the common standard. The third
round read that form and asked for twenty changes, all held. DR-0031 keeps the reasons and the
Docs Registry's section keeps the form; this design says only how the text lands.

## Goals / Non-Goals

Goals:

- The tracked tree states the one form and ETHOS's own records follow its first step.
- Every byte passes a released engine, so that no repository waits for an engine to begin.

Non-Goals:

- A check. The reports and the refusal follow in their own Changes after 0.2.0.
- A status other than accepted in any file, a banner, or the return of a removed record. They
  need the engine change of the draft `decision-record-statuses`.
- Any adopter's migration. Each keeper's lane does it.

## Decisions

1. **The text lands without its check.**
   - **Rests on:** the owner's answer of 2026-11-19 that the text lands now; DR-0029's freeze,
     which stops a new rule that can block and passes a text that refuses nothing.
   - **Considered:** waiting for 0.2.0 with text and checks together.
   - **Chosen because:** the fleet's migration takes weeks of keepers' lanes, and every first
     step passes today's engines.
   - **Applies to:** the Docs Registry's section and DR-0031.
2. **The requirement changes only where it contradicts the form.**
   - **Rests on:** the specification's rule that a requirement states an observable obligation
     with a scenario that can falsify it.
   - **Considered:** stating the four statuses in the requirement now. A released engine
     refuses three of them, so the scenario would be false on the day it landed.
   - **Chosen because:** keeping a record, making a changed ruling a new record and the one
     index can each be read from a tree today. The scenario on status and state stays as it is
     until the engine change modifies it.
   - **Shape:** the existing requirement changes its first sentence and one scenario. The rule
     that an accepted record is kept and written in the one form is an added requirement with
     its two scenarios: in the existing requirement its text would pass the specification's
     bound of 500 characters, which the archive's validation refuses.
   - **Applies to:** the delta of `repository-governance`.
3. **ETHOS's first step is the tool's output plus the marks of the updates among its records.**
   - **Rests on:** the first-step tool, which is idempotent and leaves every judgement to a
     person; and the rule that a sentence or a list item carries at most one mark.
   - **Considered:** leaving ETHOS's records until the engine change. The fleet would then
     migrate from a text whose own repository does not follow it.
   - **Chosen because:** the form's author goes first, and reading ETHOS's own records for
     their marks corrected the form three times: the unit of a mark is a sentence, not a
     paragraph; the updates are the pairs that the records' own words name, fourteen where
     memory had counted eight; and a sentence that two records had changed before the form
     carries one mark that names both.
   - **Applies to:** every file under `docs/decisions/`.
4. **The index's rows for the seven removed records name where Git holds each.**
   - **Rests on:** the form's rule that a number without a file has a row that says why.
   - **Considered:** restoring the seven now with the status accepted. Each would then claim to
     be in force.
   - **Chosen because:** a row is true today, and the records return with the status that the
     engine change lets them carry.
   - **Applies to:** `docs/decisions/README.md`.

## Risks / Trade-offs

- A text without a check is followed only as well as its reviewers read it. The conformance
  report outside the product is read at each weekly cut until the registry reports it.
- Old text stays in every tree and a search by meaning returns it. Before the engine change a
  superseded record cannot yet say so in its status; ETHOS has none in that state today.
- The marks are a reading of two records each. A wrong mark misleads more than a missing one,
  so readers other than the lead prepared each pair, and the lead ruled where they doubted.
  A pair that no word search found stays unmarked until someone reads it.
- The first-step tool reads front matter by its own small reader, not a YAML library; it
  refuses a file it cannot read and lists it for a person.
