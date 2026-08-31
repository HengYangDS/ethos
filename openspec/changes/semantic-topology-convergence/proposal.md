## Why

The repository's semantic model and its physical layout have drifted apart: a
few Python packages exist only as empty shells, some single modules are hidden
behind unnecessary package directories, and documentation topology still mixes
first-run guidance, navigation, and policy without a stable rule. This makes
ownership, discovery, and projection drift hard to see and encourages the
mechanical addition of files rather than the smallest truthful structure.

This change applies the existing deletion-first product contract to ETHOS's own
source and documentation surfaces, while preserving product semantics in their
existing authoritative owners.

## What Changes

- Define a semantic, not file-count-based, rule for Python packages: remove
  empty packages; collapse a package with one implementation module only when
  the package adds no import, lifecycle, or ownership boundary; retain a
  subpackage when it owns a real semantic boundary or multiple related owners.
- Forbid mechanical `_suffix.py` decomposition, facades, and package shells;
  move callers to the selected concrete owner and delete the superseded path.
- Make documentation taxonomy and README use follow function, authority, and
  navigation need rather than inherited directory habit.
- Resolve the previously discussed first-run placement by moving
  `quickstart.md` from `docs/start/` to `docs/guides/`, updating all links,
  stable paths, taxonomy, registry projections, and tests together.
- Preserve the existing authority boundary without claiming that a missing
  public derived view is already a product feature. This Change creates no
  lineage, predecessor/successor, hypothesis, experiment, scope, or
  granularity carrier. It verifies that topology cleanup leaves those meanings
  with their existing sources (Git/OpenSpec history, official OpenSpec
  artifacts, fresh Facts/TransitionPlan, and Attestations). Any missing public
  query surface is a separate successor concern, not a reason to add a carrier
  here.
- Recompute and verify repository projections from the selected authoritative
  sources, with repository-wide reference closure before proof.

**BREAKING**: retired Python import paths and the `docs/start/quickstart.md`
path are removed without compatibility facades or redirects.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: semantic and physical isomorphism must govern package topology,
  concrete module ownership, private boundaries, and deletion of empty shells
  without rewarding mechanical file-count reduction.
- `repository-governance`: documentation topology and first-run guidance must
  have one functional taxonomy, explicit README necessity, and projection
  closure; official OpenSpec remains the only tracked Change-intent carrier.
- `assistant-projections`: rendered and generated surfaces must preserve the
  selected source identity and current paths without becoming alternate owners.

## Impact

- Python package layout, imports, tests, and module-layout quality checks.
- `docs/` taxonomy, navigation, stable paths, registry metadata, command
  examples, and generated projection inputs.
- OpenSpec, Commitment, Attestation, Change lineage, hypothesis/experiment,
  scope, and proof semantics are audited and retained; no new semantic root,
  registry, ledger, or compatibility layer is introduced.

Out of scope: implementing new lineage or research query commands; tempfile
ownership and scavenging, runtime activation and state migration, publication
races, adopter migrations, and other lifecycle defects that require their own
successor Change.
