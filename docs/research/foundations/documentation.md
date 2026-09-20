---
subject: ethos:foundations-documentation
role: research
state: active
relations:
  part_of: ../modern-engineering-foundations.md
  informs: ../../governance/docs-registry.md
  constrained_by: ../../governance/product-design-contract.md
---

# Documentation And Knowledge Interchange

Status: active research; target requirements are not implemented guarantees.

Purpose: evaluate human and agent comprehension, metadata and navigation
without creating another authority.

See also: [Research Overview](../modern-engineering-foundations.md),
[Documentation Governance](../../governance/docs-registry.md),
[Intent And Adoption](adoption.md), and
[Terminal Plan](../../plans/terminal-governance-product-design.md#open-knowledge-format--bounded-adoption-assessment).

## Question And Conclusion

Documentation preserves meaning and enables supported understanding, decisions
and action. A short file, metadata completeness or valid links cannot establish
that outcome. The same accepted meaning must serve human reading and agent
retrieval without becoming separately edited knowledge stores.

| Question | Read |
| --- | --- |
| What should OKF contribute, and what must remain native? | [Format fit](#format-fit) and [source assessment](#source-assessment) |
| Which metadata is necessary? | [Metadata design](#metadata-design) |
| Which defects were actually reproduced? | [Executed counterexamples](#executed-counterexamples) |
| How should quality and thresholds be evaluated? | [Dual-reader acceptance](#dual-reader-acceptance) |

## Format Fit

[OKF 0.2][okf] is a knowledge-interchange research candidate, not a mandate to
restructure the repository. Its source/provenance/freshness relationships are
useful; its permissive unknown-field and broken-link handling cannot be copied
into trust-bearing admission. Optional index conventions do not justify adding
unnecessary index files. Export an accepted semantic view if a consumer needs it;
do not import a second intent, attestation or task system through documentation.
[Diataxis][diataxis] helps distinguish learning, practical guidance, explanation
and reference; it does not dictate a file-count rule or erase decision rationale.

The upstream default branch was read again on September 20, 2026 and resolved
to the same pinned commit used below. This verifies the selected source, not
ecosystem maturity or an executed ETHOS interchange adapter.

## Source Assessment

The September 11 review examined [OKF v0.2](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/ad30107c31c06aec8a7d5636e0d1058118604e6f/SPEC.md)
at exact upstream commit `ad30107c31c06aec8a7d5636e0d1058118604e6f`.
Recommendation: evaluate OKF as an optional knowledge exchange projection, not
as a replacement for accepted intent, document governance or effect admission.
The format requires no runtime and leaves domain organization to producers.
This assessment introduces no dependency, document migration or second plan.

| Disposition | Source observation | ETHOS consequence |
| --- | --- | --- |
| Adopt the portable representation where needed | Markdown/YAML concepts, source references and ordinary links support human and tool interchange. | Derive a bounded bundle from existing owners; imported material remains input to interpretation and acceptance, never an instruction to mutate. |
| Map, do not equate, metadata | OKF `type` classifies a concept; ETHOS Subject, Role, State and Relations express different responsibilities. | Preserve distinctions and unknown extension fields. Do not mechanically rename Role to type or duplicate manually maintained state. |
| Separate consumption from admission | OKF consumers tolerate broken links and missing optional fields; missing status means stable. | Accept format-valid material without promoting it to accepted/current ETHOS meaning. Report unresolved references and apply the relevant native obligation before use. |
| Preserve provenance without inheriting authority | Trust tiers are advisory and derived from actor labels in verified metadata. | Bind upstream claims to their original source and revision. Human-prefixed text, imported verification or successful parsing cannot establish local identity, authorization or currentness. |
| Keep necessary identity distinctions | OKF concept identity is its bundle path without the Markdown suffix; link relation types remain prose. | File movement must not silently change ETHOS semantic identity. Preserve Subject and typed Relations in an explicit mapping or report the loss. |
| Reuse existing navigation and history | index.md and log.md are optional. | Do not recreate directory indexes, duplicate README navigation, mirror external evidence or add a parallel change log merely for conformance. |
| Defer executable integration | Executor packaging, attester ABI/sandboxing and full receipt/verdict wire formats are outside the current specification. | Attested Computation is not ETHOS Attestation. Never auto-execute imported resources; any future adapter uses the existing capability and fresh-admission boundaries. |

Upstream [issue 15](https://github.com/GoogleCloudPlatform/open-knowledge-format/issues/15)
reports ambiguous imported verification provenance and proposes an imported
field. It was open at review time: it is supporting research, not a standardized
field or evidence that the proposed repair works. Retain this boundary explicitly
instead of silently treating foreign review as local verification.

The smallest useful trial belongs to the existing P1/P7 context and ecosystem
work after the current quality closeout. Select one actual external consumer
and a bounded set covering a canonical definition, a decision and a guide;
compare native consumption against export/import. Verify source/Subject binding,
unchanged meaning and typed relations, explicit unresolved or lossy mappings,
unknown-field preservation, rename behavior and no inherited trust or execution.
Do not flatten document purpose into one template. No index or duplicated
knowledge store is required. Measure reduction in consumer-specific glue and
manual continuation effort before retaining an adapter. If there is no real
consumer or no net reduction in complexity, retain the findings, not an unused
implementation. This trial and conformance are not yet executed.

## Metadata Design

Evolve the existing registry as a small typed contract, not a larger mandatory
form. The following are design recommendations, not an implemented schema.

| Concern | Recommended representation | Avoid |
| --- | --- | --- |
| Identity | Existing stable subject; paths locate it. | Renames silently changing meaning or adding a second ID for OKF. |
| Reader purpose | Existing role expresses document function; directories express subject containment. | Equating OKF concept type with reader purpose or imposing one template. |
| Lifecycle and authority | Explicit lifecycle, authority relationships resolved against accepted sources. | Treating canonical labels, timestamps or actor strings as permission or proof. |
| Relationships | Typed values distinguish paths, subjects, external sources and scope descriptions. | Flattening relations into strings or guessing all values are paths. |
| Sources and applicability | Source revisions, scope and assumptions where a claim requires them. | Mandatory empty decoration or duplicating complete source material. |
| Freshness | Observations bind evidence and relevant dependencies. | File mtime or a universal expiry period masquerading as verification. |
| Display and history | Derive titles, breadcrumbs, backlinks and Git history when already owned. | Independently maintained status, title, version or author copies. |
| Extensions | Unknown imported fields remain inert and preserved; known fields validate strictly. | Silent loss, inherited foreign authority or automatic execution. |

Every retained field needs a real consumer and meaning that cannot already be
derived reliably. Schema versions belong to the protocol boundary, not ordinary
filenames. No metadata field certifies its own authority or freshness.

Use a native YAML parser and existing schema capabilities rather than custom
frontmatter syntax. Select one schema owner; if CUE owns the contract, generate
other schema views instead of manually maintaining equivalent rules. A useful
OKF integration requires a real consumer and explicit mapping, not merely adding
its required type field to every document.

## Executed Counterexamples

On September 20, 2026, isolated documents were passed to the installed public
docs-registry report adapter, loading the real command tree and shared health
owner. Source: 684823165b48c8d18ded89969fbfaeee15dd14f5.
Runtime: 12e1dcb17fae62c59976a4c8e17084732f60ccc9a585162b9fcc4c21c3aadd92.

| Input | Observed | Required distinction |
| --- | --- | --- |
| Plain valid metadata | PASS | Preserve this legal path. |
| Quoted YAML role and state | BLOCK | Equivalent valid scalars preserve meaning. |
| Duplicate state keys | PASS | Ambiguous declarations cannot silently choose one value. |
| Missing closing frontmatter delimiter | PASS | Body text cannot become a valid header. |
| Current-owner relation points to a missing document | PASS | Required authority targets resolve. |
| Canonical header with superseded visible status | PASS | Human and machine views cannot disagree. |
| Required visible labels appear only inside a fenced example | PASS | Literal examples are not actual page guidance. |

The inspected owner splits lines and flattens nested fields; visible-section
checks search raw text. These mechanisms explain the sampled outcomes.
The samples exercise this report, not every gate or full-proof admission.
They do not establish that a release bypass occurred.

Exact samples and reports are in the existing ignored evidence location
build/evidence/quality/commit-integrity/document-metadata-public-probes.json.
SHA-256: b4845f4cac592e73845486a2c1f4a405b2ce505c44b22c089cbd6bccd09fa955.
All owned fixtures were removed. Parser repair, migration and installed
requalification remain unproved.

## Dual-Reader Acceptance

Use rendered reading, raw Markdown and agent retrieval on the same source.
Evaluate whether a reader can locate the current rule, explain its rationale,
find prerequisites and exceptions, identify contrary evidence, and choose a
supported next action. A correct answer identifies the source and applicable
scope, not merely matching words.

Measure correct completion, wrong-authority selection, unnecessary context,
backtracking and time to supported answers. Human time and agent tokens/tool
calls remain separate. Document roles and language matter; characters/100 is
neither comprehension nor a justified universal threshold.

Proved integrity defects can block: malformed known metadata, ambiguous identity,
unresolved required relations, contradictory authority and lost meaning.
Size, depth and link counts are diagnostic until calibrated against reader tasks.
A necessary worked example can be better than several tiny linked fragments.

[Diataxis][diataxis] distinguishes reader needs rather than prescribing folders.
[Meaningful link purpose][link-purpose] and
[descriptive headings and labels][headings-labels] guide human navigation.
Machine access needs relation direction/type, stable subjects, source binding
and explicit unresolved references. Derived graphs can check reachability and
relation-specific cycles; ordinary reciprocal navigation is not an error.
The graph is rebuildable, not a second editable catalog.

The existing [official Change](../../../openspec/changes/proof-throughput/tasks.md#documentation-comprehension-and-research-delivery)
owns progress. Repair the reproduced owner defects, then compare retrieval
before/after reorganization and execute the bounded consumer trial. No reader
study, interchange conformance or whole-corpus migration is claimed here.

## Sources

[okf]: https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/ad30107c31c06aec8a7d5636e0d1058118604e6f/SPEC.md
[diataxis]: https://github.com/evildmp/diataxis-documentation-framework/blob/957c09ca40b4a1edc23874f713e01937d50d54d5/README.rst
[link-purpose]: https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context.html
[headings-labels]: https://www.w3.org/WAI/WCAG22/Understanding/headings-and-labels.html
