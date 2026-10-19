# Design

## Context

Prewrite resolves OpenSpec governance once. When a bounded repair scope exists, the prewrite verdict comes only from that scope's own gaps: requested paths it authorizes pass, and every other path reports `openspec_material_path_uncovered`. Two sources open a scope today, canonical spec repair and active-Change strict validation repair, and both derive from official strict validation failures. Template drift is reported by ETHOS while the official validator accepts the Change, so neither source opens and the drift cannot be repaired. The proposal states the resulting deadlock; the `repository-governance` delta states the required behavior.

## Goals / Non-Goals

**Goals:**

- Make template drift repairable from the owning Work Lane without weakening any other admission check.
- Keep one repair mechanism: template drift becomes one more evidence source of the existing repair scope, not a parallel admission path.

**Non-Goals:**

- Changing what the template requirement demands or its repository-wide blocking.
- Repairing an unreadable template or an unreadable artifact; those gaps are not drift.
- Admitting any path outside the selected Change.

## Decisions

### Template drift is the last repair source

The repair scope tries canonical spec repair, then active-Change validation repair, then template conformance repair for an active, unarchived Change. A Change with both a validation failure and drift repairs the validation first; its drift repair opens once validation passes. Merging the sources into one union was rejected: each source's admission context stays independent and individually verifiable.

### Every blocking gap must be template drift

The source opens only when every required governance gap is a template-heading gap, as the validation repair opens only when its own gaps are the sole blockers. Any other gap, such as an unavailable official CLI, keeps the repair closed, so a repair never stands in for an unrelated check.

### Another Change's drift may coexist

Requiring that every gap belong to the selected Change was rejected: two drifted Changes would then hold each other's repair indefinitely. The source accepts any template-heading gap but authorizes only the selected Change's drifted artifacts, so each Change is repaired once it is selected.

### Paths come from the already-confined official outputs

The selected Change's official status names the output files of each artifact. The source selects the drifted artifacts' files from the official output list that the caller has already confined to the repository. Importing the governance path helper instead was rejected, because it would close the import cycle `governance → lifecycle.report → lifecycle.scope`.

### The gap prefix has one owner

The template conformance module produces template-heading gaps and defines their prefix; the repair source imports it rather than restating the literal.

### Template repair has its own module

The repair source lives in `lifecycle/template_repair.py`, so the scope module keeps only the call and the next action and stays within its size budget.

## Risks / Trade-offs

- [A drifted artifact may be edited beyond its missing headings while the repair is open] → The repair admits only the drifted files, and proof and commit admission still apply the full template and strict validation checks before anything lands.
- [The source reads the artifact name from the gap text] → It parses only gaps that ETHOS itself produces, splitting at the first three colons so that a heading path may contain a colon.
- [Adopters must update their runtime to obtain the repair] → An adopter already held by drift updates its runtime first, then adds the missing headings from its own Work Lane.
