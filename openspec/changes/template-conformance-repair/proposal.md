# Proposal

## Why

ETHOS requires every active Change's proposal and design to carry the literal headings of its official template. A Change whose artifacts predate that requirement, or drift from it, still passes official strict validation, so the bounded repair entry, which admits only files that strict validation names, never opens. Every prewrite in the repository then blocks on the template gap: the drifted artifact, an unrelated file, and even an exact patch that restores the missing heading. The commit hook rejects the drift as well. An agent can neither write the repair nor anything else, so an adopter whose active Change predates the requirement is locked out as soon as it moves to a runtime that enforces it.

## What Changes

- When every blocking OpenSpec gap is a template-heading gap, prewrite admits the selected Change's drifted proposal and design files, and only those files, as bounded repair paths through the existing repair scope.
- Every other requested path stays blocked as uncovered, and any blocking gap other than template drift keeps the repair closed, so the repair bypasses no other check.
- Another active Change's drift does not hold the selected Change's repair; each drifted Change is repaired once it is selected.
- The repair names `ethos status --json` as its next action, because ETHOS, not the official validator, reports template drift.
- Out of scope: relaxing what the template requirement demands, its repository-wide blocking, and repairing an unreadable template or artifact.
- No breaking change: a repository without template drift observes no difference.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: an active proposal or design that drifted from its official template is repairable through bounded repair admission.

## Impact

- Code: `src/ethos/adapters/openspec/lifecycle/scope.py`, a new `src/ethos/adapters/openspec/lifecycle/template_repair.py`, and `src/ethos/adapters/openspec/template_conformance.py`, which now defines the template-heading gap prefix it produces.
- Adopters held by template drift repair it from their own Work Lane after updating to a runtime that contains this Change.
