# Design

## Context

See [proposal.md](proposal.md). Owner decision D3 binds this Change. Revision 5.1 (`build/runtime/work/architecture-realization/knowledge-system.md`, "Normative owners" and "Dispositions") names the scope and gives each orphan document a first destination.

Five read-only audits at `ad9108d70` placed every statement, with file and line evidence. Their reports are this Change's evidence (`build/runtime/work/fbee0c-session/normative-layering/audits/`):

- N0: the consumers of the 11 documents;
- N1: openspec-governance, skills, independent-verification-adoption, authority, product-boundary-convergence and standards-adoption-policy;
- N2: release-governance and forge-provider-contract;
- N3: repository-profile-contract, config-boundary-model and adopter-boundary-and-retirement;
- N4: rules, system and documentation metadata;
- N5: the proof-hosts spec.

Constraints:

- **Shipped documents.** The wheel ships the PDC, the Docs Registry, the kernel model, the glossary, the command plane, the quickstart, `rules/` and five of the eleven documents (`pyproject.toml`). A shipped document may link an unshipped one only with the `"source-only"` link title.
- **Size.** Every Markdown file, including each delta file, stays within 512 nonblank lines. A requirement's text stays under 500 characters.
- **Budget.** `python_product` is at 69,999 of 70,000, so the consumer edits must not grow it.
- **Concurrency.** This Change edits no PDC or TP line. `docs/architecture/runner-and-mutation.md` belongs to `one-proof-per-change`; this Change repairs only its link to a retired document, with that owner's agreement. `shared-quality-obligations` starts after this Change lands, because both edit `repository/policy/rules/compile.py`.

## Goals / Non-Goals

**Goals:**

- No orphan policy document remains: every statement of the eleven has an owner, a non-normative home, or a recorded reason to go.
- Every consumer, link and pointer moves in the same Change, and `ethos context` keeps its reader roles.
- The carriers that explain the hierarchy (rules index, module layout rule, axioms, `system/*.toml` headers, documentation metadata) cite owners that exist.

**Non-Goals:**

- New behavior. Each requirement added here states what the code already does, or a process obligation that an accepted decision binds and review verifies: the comparative-assurance group (DR-0014, reviewed in the retirement judgment) and the release stages (DR-0015, reviewed in the release entry).
- Mechanical reference checks; `knowledge-checks` adds them.

## Decisions

### One Change

The eleven documents share one intent, and their consumers overlap: `audit.py`, `context.py` and the wheel list name documents from both halves. Splitting would add two full proofs on the shared proof slot and land `compile.py` no sooner. PDC 569-573 admits a split only when each part lands a useful outcome without duplicating authority; this Change is reviewable as one outcome.

### Dispositions

Each statement takes one of four routes:

- **Covered.** A statement that a normative owner already states becomes a link to that owner, or goes when the reader no longer needs the link.
- **Unique obligation.** A statement with no other owner moves to that owner as a requirement or a configuration rule.
- **Non-normative.** Explanation, reference and procedure move to an existing document or a new how-to, which links the owners and restates none.
- **False or unread.** A false statement, a self-description or a classification nothing reads goes, with its evidence in the audit.

| Document                          | Statements | Covered | Stale  | Unique obligations | Non-normative moves | Dropped |
| --------------------------------- | ---------- | ------- | ------ | ------------------ | ------------------- | ------- |
| openspec-governance               | 55         | 49      | 0      | 2 (configuration)  | 1                   | 3       |
| skills                            | 42         | 39      | 1      | 0                  | 1                   | 1       |
| independent-verification-adoption | 31         | 25      | 1      | 1                  | 3                   | 1       |
| authority                         | 10         | 8       | 1      | 0                  | 0                   | 1       |
| product-boundary-convergence      | 8          | 6       | 0      | 0                  | 0                   | 2       |
| standards-adoption-policy         | 10         | 6       | 0      | 0                  | 0                   | 4       |
| release-governance                | 93         | 67      | 1      | 15                 | 6                   | 4       |
| forge-provider-contract           | 35         | 23      | 5      | 0                  | 3                   | 4       |
| repository-profile-contract       | 85         | 68      | 11     | 2                  | 3                   | 1       |
| config-boundary-model             | 21         | 15      | 2      | 2                  | 1                   | 1       |
| adopter-boundary-and-retirement   | 22         | 7       | 0      | 13                 | 1                   | 1       |
| **Total**                         | **412**    | **313** | **22** | **35**             | **19**              | **23**  |

### Where the unique obligations go

- **repository-governance.** Seven requirements go here:
  - "Control-replacement receipts bind the trusted predecessor": the four independent-verification requirements already live here, so it is not split into proof-hosts, as revision 5.1 first suggested;
  - "OpenSpec lifecycle applicability follows observed facts";
  - "CI runner and retained-step records own their commands";
  - four comparative-assurance requirements (next section).
- **distribution.** Three requirements: version compatibility, prerelease stages, and release candidates and stable releases. DR-0015 keeps their rationale; release preparation and its entry are their verifier, since no checker exists.
- **adapters.** "Forge review observation uses declared API coordinates."
- **quality.** "Isolated Python static analysis judges the declared target." This is the one quality delta of this Change. `shared-quality-obligations` rebases onto it.
- **openspec/config.yaml.**
  - The withdrawn-task form moves into `rules.tasks` and `rules.specs`. DR-0016 named openspec-governance as its owner.
  - The duty to move durable design rulings to their owner before archive moves into `operations.archive.guidance`.

### Comparative assurance is accepted ahead of a checker

The comparative contract governs a replacement execution substrate's takeover from an incumbent: equal or stricter, admitted corrections, blocking outcomes and the retirement judgment. No code implements it. DR-0014, accepted on 2026-10-18, binds it and says a future checker will implement it; until then, retirement judgments record corrections.

The four requirements go to repository-governance as process obligations. Their scenarios can be falsified by reviewing the retirement judgment and the effects it authorizes, and they stay true when a checker arrives.

Alternative rejected: keeping the contract in an explanation document. That would leave a normative statement in a non-normative carrier, which D3 forbids. An edit to DR-0014's decision text is ruled out too, because accepted decisions are immutable (K4).

### Decision-record pointers are live relations

`current_owner` is a live relation (Docs Registry, retained-record rule), and the registry requires its target to exist. Each pointer, status line and "See also" link that names a retired document therefore moves to its new owner:

- DR-0006 → repository-governance;
- DR-0012 → the repository-paradigm spec;
- DR-0014 → the repository-governance spec;
- DR-0015 → the distribution spec;
- DR-0016 → `openspec/config.yaml`.

No Context, Decision, Alternatives or Consequences text changes, so K4 holds.

### Agent context keeps its roles

`ethos context` serves sections of shipped documents. The roles `adoption`, `release` and `recovery` pointed at three retiring documents. They now point at shipped owners:

| Role     | New source                                                             |
| -------- | ---------------------------------------------------------------------- |
| adoption | the PDC's Binding Taxonomy, Configuration Boundaries and First-Hour UX |
| release  | `rules/release.md`                                                     |
| recovery | the PDC's Runtime And State Authority and Bounded Maintainer Recovery  |

The installed-guidance test keeps its role set.

### proof-hosts currency

Audit N5 found parity, claim admission, promotion targets, a `proof-hosts` package that never existed, a finished migration campaign and a retired process-identity scenario:

- Four requirements keep their titles and restate their full text: lifecycle fixtures, reference adopter fixtures, hosted provider observations and Skill conformance fixtures.
- Two carry a false scenario title, so each is removed and added under a name that states the obligation: proof separation, and host Git semantics.
- The migration-closure requirement is removed, and the full proof set's gates and three accepted requirements own what remains of it.
- A delta cannot change a Purpose, so the proof-hosts Purpose is edited in the spec file.

Its true claims without a current regression are listed in N5. They are coverage gaps, not text errors, and they go to the product lane.

### Restored tasks

- **documentation-comprehension 12.3 (environment).** The agent half navigates from the governance index and the Docs Registry to each subject's owner in this Change. The human half is the owner's review of the result.
- **12.3.3, ETHOS side.** Every required front matter field has a registry consumer:
  - `subject`: duplicate-subject detection;
  - `role`: the taxonomy check;
  - `state`: lifecycle and visible-status consistency;
  - `relations`: owner targets must exist.

  None can go, so the reading cost is that of these four fields. The DDWG side stays with `adopter-conformance`.

- **12.4.1** (auditing the historical over-limit reductions) moves to `knowledge-checks`, which restores its parent 12.4. a225 accepted the move on 2026-10-28 and records it in the restoration map.

### Consumer-less configuration goes

`.ethos/rules.toml` declares four tables that nothing reads: `[standards]`, `[determinism]`, `[formats]` and `[artifacts]`. The rules configuration parses only `[profiles]` and `[[rule]]` (audit N4). `[standards]` uses the adoption-level vocabulary of the retiring standards policy, and is that vocabulary's only use.

All four go. `system/formats.toml` keeps its format assignment as the loaded product carrier contract. Revision 5.1 assumed the opposite direction (`formats.toml` stops repeating `.ethos/rules.toml`), but the owner with a consumer is the one that stays.

### Kept, or owned elsewhere

- **The kernel role set.** It keeps `findings` and `progress` (`src/ethos/repository/registry/docs/registry.py`). The taxonomy lists the same set, so removing a role is a product change with a fleet check of adopter documents. It goes to the product lane.
- **`VERSION`.** It stays the next release target, as distribution states. Practice leaves it at the released version between releases, so post-release development builds sort before the release. That is a release-process defect for the product lane, and the spec is not reworded to match it.
- **Product defects found by the audits.** Each goes to the product lane:
  - Release Policy's in-repository executable rule against the PATH lookup in `publication.py`;
  - Skill activation never matching by operation (`domain/plan.py`);
  - adoption writing `openspec/config.yaml` while repository-governance says it plans no OpenSpec carrier;
  - the profile fields `roots.rules` and `[adoption_boundary]`, which have no reader.

## Risks / Trade-offs

- [A shipped document gains a link to an unshipped one] → Every such link takes the `"source-only"` title, and the installed-navigation test runs before proof.
- [Agents lose guidance they relied on] → The context roles stay. Each retired section's true content is in the new source, or in an owner the new source links.
- [A moved requirement states behavior the code does not have] → Each moved requirement cites the code that implements it, or the accepted decision whose process it states (DR-0014, DR-0015).
- [The Change is large] → Tasks follow the document groups, so review and proof stay ordered. The strict validation and the archive simulation run before proof.
