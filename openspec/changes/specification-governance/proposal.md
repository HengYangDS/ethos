# Proposal

## Why

Accepted specifications are the one tracked text that no size rule of this product reaches. The
`quality` requirement on the document ceiling exempts them and leaves them to "semantic capability
review", which no step performs. Read in this repository's batch lane on 2026-11-16: one
capability holds 221 requirements in 5,117 non-blank lines and a second 149 in 2,865; five
capabilities hold more than 30 requirements.

Governed repositories met the gap in two ways, reported by the session that keeps two of them:

- One keeps a gate of its own on the lines of a specification. It measured an active delta in
  place of the specification that the delta rewrites, and an archive then produced a
  specification above the gate's value after a passing check.
- One has no gate. A specification of 716 non-blank lines stands there, and its one open Change
  would bring it near 1,050 at the archive.

A ceiling on lines would repeat the first case everywhere, and text can be fitted to a count.
The owner therefore mandated an expert committee on 2026-11-16, in that session: five seats
(requirements engineering, governance mechanism design, maintenance and delivery, agentic use,
evidence audit), six rounds, and a resolution that all five accept, adopted the same day.

Status of the direction: the owner confirmed on 2026-11-16, in that session and then first-hand
in the release lead's, that ETHOS implements the resolution. The release that reports and the
release that arms are not placed.

The record (the brief, the rounds, a research packet and the resolution, 49 files) names governed
repositories and their figures, so it is not tracked here. A byte copy is in the release lead's
local evidence, `build/evidence/spec-governance-committee-20261116/`; the resolution's SHA-256
begins `f33f5fc59d4dd9f1`.

The same exchange restated that every per-file ceiling of this product is 500 lines. One
decision record still named 512, which a later record calls stale. The documents row of the
batch that holds this draft, `command-reference-split`, corrects that sentence; nothing of
this Change is built.

## What Changes

What the resolution asks of this product, in the order in which it arrives. None of it is built.

- **A release that reports everything, and refuses nothing new.** For every capability that a
  Change touches: requirements, scenarios for each requirement, steps and SHALL and MUST for each
  scenario, lines and bytes, the largest block. Every measure is taken on the archive result at
  each check of an open Change, never on a delta in place of its specification.
- **The release after it arms the structural refusals,** each after its reports were answered:
  - Growth only. `size.capability_requirements` (default 30, bound 45) and
    `size.requirement_scenarios` (default 10, bound 20). A unit above its value is reported as it
    stands; a Change is refused only when it leaves the unit above the value and larger than at
    its base. A split into the successors that a `REMOVED` block names is not growth.
  - A requirement's title is its identity. One resolver and one form of citation; a citation that
    resolves to no title of the archive result is refused, and the refusal names the current or
    the succeeding title.
  - Three routes change an accepted specification: an archive; a conserving move, which relocates
    whole requirement blocks byte for byte and which the product proves; and a retiring edit for
    scenarios, which the Change lists and the product compares with base and head.
  - A Change that removes a path which an accepted requirement cites also changes that
    requirement. A `REMOVED` block carries its reason, its migration and its successors' titles.
- **Then** a generated, untracked index from each declared surface element to the titles that
  name it, and closed lists for the surface classes that a repository's owner declares public;
  **then** verifiers that cite the titles they verify; **last** the rules that this product
  enforces on every governed repository, stated here and nowhere else.
- **Content is asked, not measured.** Fixed review questions on a sheet that the product
  generates, answered by a reviewer other than the author. The product refuses only a missing
  record, after a release that reported it.
- **No rule that the scheme adds refuses on an amount of text.** The lines, characters and bytes
  of a specification are reported. Two refusals on an amount of text stand outside the scheme,
  both OpenSpec's, through this product's strict validation: a requirement statement above 500
  characters and a Purpose under 50. The resolution measures how statements bunch below 500
  characters, and that measure decides whether this product asks upstream to change the first
  or stops refusing on it.
- **The test that every later rule passes.** An obligation has a performer, an input, a moment
  and a recorded result. It refuses only where a machine decides it the same way on every run,
  the author can repair it inside the refused Change, and the cheapest way to pass is the
  wanted repair. What fails that test is reported or asked.
- **A Change does not remove the last verifier** of a requirement that it neither modifies nor
  removes: a refusal, base against head.
- **Of the named principles, one enters by name:** a single source of truth. The others enter
  as plain obligations or are rejected for specifications, as the owner asked the committee to
  rule.
- **Retired here:** the exemption of accepted specifications, the phrase "semantic capability
  review", and the precondition that a split waits for a capability without open deltas.
- **This repository's own specifications:** a capability above the value takes no new requirement
  other than the parts of a split, and the reduction starts with the largest capability.

The committee states what it did not prove. The values come from the distributions of four
repositories and from no study. Nothing that this product must build exists: the resolver and the
citation form, the sheet and its record, the index, the acceptance digest's entries for a retired
scenario, the comparison of blocks for a move, the titles that the runtime ships, and the
generated worklist of what stands above a value, ranked by how often each requirement is
edited, with the report of its head and age. The resolution names its own measures, read on
2027-02-16, and no performer for them: the release lead reads them, and the design says so.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

`quality` (the document ceiling and its exemption), `repository-governance` (the OpenSpec
admission and the simulated archive), the paradigm's size rows, the acceptance digest, the review
record and the runtime's build. It is several rows and at least one decision record; the existing
record that refuses an exception for one unit stands.

It adds law: new values and, one release later, new refusals. The plan to 0.2.0 admits one
off-gate row a batch and no new rule, so the release that reports and the release that arms are
the owner's to place. The session that keeps the two governed repositories plans around both: one
retires its own gate when it binds the runtime that carries the mechanism, the other archives its
open Change within the reporting release.

Owner: the release lead. Next action: size the reporting release as rows; put the two releases
to the owner at the cut of 0.2.0-beta.12, and tell that session which they are. Read again:
2026-11-19.
