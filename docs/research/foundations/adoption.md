---
subject: ethos:foundations-adoption
role: research
state: active
relations:
  part_of: ../modern-engineering-foundations.md
  informs: ../../plans/terminal-governance-product-design.md
  constrained_by: ../../governance/product-design-contract.md
---

# Intent, Adoption And Learning

Status: active research; dated observations retain their original evidence limits.

Purpose: Evaluate intent fidelity, provenance, repository formation and outcome feedback.

See also: [Research Overview](../modern-engineering-foundations.md),
[Product Design Contract](../../governance/product-design-contract.md), and
[Terminal Plan](../../plans/terminal-governance-product-design.md).

## Intent Formation And Official OpenSpec Extension

[Official OpenSpec customization][openspec-customization] supports project
context and per-artifact rules, with custom schemas when actual artifact
dependencies need to differ. Prefer the smallest native extension that expresses
an accepted need. Use custom schemas only after testing official generation,
status, validation, synchronization and archive; do not fork the parser or copy
its task state machine into ETHOS.

For the full intent path, keep source observations and unresolved interpretations
explicit, read back positive and negative cases, then accept one meaning before
deterministic compilation. An all-drop exploration cannot be translated into a
mandatory winner. Schema validity and provenance coverage do not prove that the
interpretation is correct or the checks are sufficient to falsify it.

Implementation acceptance and post-archive publication outcomes are different
obligations. Do not require an immutable archive to hold future mutable task
progress, nor check off publish/retire before their effects. Use an already owned
release operation or subsequent official Change where appropriate, retaining
source/result links and the full delivery goal. The reported adopter task cycle
requires a public-path regression; this research has not established a currently
working accepted-runtime solution or created another release carrier.

## Supply, Adoption, Knowledge And Learning

[in-toto statements][intoto-mechanism] and [DSSE envelopes][intoto-envelope] offer
subject/predicate and signed-envelope interchange. [SLSA tracks][slsa] distinguish
source and build assurances; [TUF][tuf] addresses trusted software updates; a
[CycloneDX SBOM][cyclonedx] describes supply contents. Reuse these boundaries where
cross-system consumers exist. Signatures and digests alone do not prove current
authority, independent verification or actual benefit. Standard adapters must
preserve the original Attestation identity and never create a second result owner.

[Copier's update mechanism][copier-mechanism] is a strong scaffold/upgrade candidate:
retain the template revision and answers, reapply user changes and surface
conflicts. Its generated candidate still requires ETHOS acceptance. Greenfield
can retain that upgrade basis from generation; brownfield must preserve native
layout and user customizations rather than pretend it was generated. Template
answers are generation provenance, not another intent store. Test deletion,
conflict, cancellation, upgrade and exit, including removal of owned hooks and
references without deleting user material.

Documentation format, metadata and human/agent navigation are evaluated in
[Documentation And Knowledge Interchange](documentation.md).

Use native CLI/schema/API generation where it eliminates independently editable
copies. Verify meaning, not merely hashes or links. The architecture consumer's
R01–R14/P00–P09 report exposes a useful falsifier: current quality-contract lists
named obligations without definitions found in the inspected source surfaces.
Resolve the original owner/history; export necessary definitions or evidence-based
replacement mappings. G-series counts and rendered geometry cannot substitute
for undefined named criteria. This is a pending repair, not a concluded deletion.

[Inspect AI][inspect] and [DSPy][dspy] are candidates for evaluating and improving
replaceable interpretation/research capabilities. Preserve input sources, accepted
meaning, counterexamples and held-out workloads. Learned scores cannot compensate
for violated hard constraints, and observers cannot edit accepted criteria or
acquire write permission. A useful end-to-end result connects a deployed identity,
environment, baseline and observation window to the original objective; a green
build or successful deployment is not that result.

## Sources

Links identify inspected documents, not blanket endorsements. Source-level and
README observations above have different strength; repository popularity and
marketing claims were not used as evidence of comparative performance.

[intoto-mechanism]: https://github.com/in-toto/attestation/blob/2dcd055e9f72e746687c306e35f4e59720ff45be/spec/v1/statement.md
[slsa]: https://github.com/slsa-framework/slsa/blob/54b88b009fd45acb331c7e6578a526e0f36e0430/spec/tracks.md
[tuf]: https://github.com/theupdateframework/python-tuf/blob/d6b4392ea0620e2eae32f55bf317afd1009c0096/README.md
[cyclonedx]: https://github.com/CycloneDX/specification/blob/595d98f16159bdf7463adc140509ded479130b8b/README.md
[copier-mechanism]: https://github.com/copier-org/copier/blob/217e4f87828694df89e1513a1febdc33792f6e89/docs/updating.md
[inspect]: https://github.com/UKGovernmentBEIS/inspect_ai/blob/8ebe620d74c1eb679438db1b65324e30e2306092/README.md
[dspy]: https://github.com/stanfordnlp/dspy/blob/ecba33763316d2a4c6c756046a1118ecbff033e7/README.md
[intoto-envelope]: https://github.com/in-toto/attestation/blob/2dcd055e9f72e746687c306e35f4e59720ff45be/spec/v1/envelope.md
[openspec-customization]: https://github.com/Fission-AI/OpenSpec/blob/9d4e5974e5c0d9a09b9c6c1e1eb0975e80ec4461/docs/customization.md
