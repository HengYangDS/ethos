## Context

See `proposal.md` and the modified requirements. The repository already has
module-layout checks, a Docs Registry, official OpenSpec artifacts,
Commitment/Attestation contracts, and projection export checks. These owners do
not yet form one repository-wide closure for physical layout and documentation
movement. The former onboarding root also remains despite the functional
placement decision to use `guides`.

## Goals / Non-Goals

**Goals:**

- Make semantic ownership, not file count, decide whether a Python package or
  README exists.
- Remove empty shells, unjustified single-module packages, suffix facades, and
  stale physical paths after moving their consumers.
- Move ETHOS's quickstart to `docs/guides/quickstart.md` and make docs indexes,
  taxonomy, stable paths, links, registry output, and generated projections
  agree.
- Preserve the existing authority boundary without silently expanding this
  Change into a missing product feature: topology work creates no lineage,
  research, scope, or granularity carrier. Existing Git/OpenSpec/Facts/
  TransitionPlan/Attestation owners remain untouched; if a public derived view
  is absent, that is explicitly deferred to a separate successor rather than
  filled with a new registry or field here. Commitment remains only the
  transient acceptance compilation.
- Leave one machine-checkable reference and import closure after every move.

**Non-Goals:**

- No new semantic root, feedback ledger, dependency database, workflow state,
  compatibility facade, redirect page, or negative exception registry.
- No changes to tempfile ownership, runtime activation, Lease migration,
  publication, adopter repositories, or the closed hosted-runtime atomic.
- No mechanical flattening of a package that genuinely owns a namespace,
  resource boundary, registration boundary, or independent invariant.

## Decisions

### 1. Semantic ownership decides physical shape

Use the existing module-layout policy and repository reference closure as the
decision point. An empty leaf package disappears. A single-module package is
collapsed only when the package contributes no public or operational boundary.
A parent containing child packages is not empty merely because its initializer
has no code; it is retained only if its namespace is a real boundary. A real
multi-owner split uses a semantic subpackage, never a flat `_suffix.py` family.

Alternative rejected: deleting every one-file directory or retaining every
initializer. Both confuse physical shape with semantics.

### 2. Documentation roots name function, not lifecycle

Use the Docs Registry metadata for subject, role, state, and relation. For
ETHOS, onboarding is a guide, so the canonical first-run document is
`docs/guides/quickstart.md`; the former onboarding path is removed rather than
redirected. Adopter layouts remain profile-native because semantic isomorphism
does not require physical uniformity.

README is an index or boundary carrier, not a directory marker. A directory
with one document does not gain a README by convention; a README survives only
when it adds navigation or boundary meaning its children cannot carry.

Alternative rejected: universal README-per-directory and universal README
prohibition. Both lose semantics.

### 3. Existing product roots retain product semantics

The Change does not recreate lineage or experimental entities, and it does not
pretend that absence of a public query surface is an implemented feature. Git
ancestry and official OpenSpec history remain the ordinary history sources;
authored hypotheses and experiment procedures remain official OpenSpec
content; exact observations and conclusions remain Attestations; Change
progress stays in official `tasks.md`; and scope/granularity remain admission
and proof facts where those projections already exist. A missing derived view
is a model gap for a later successor, not permission to add a DAG database,
experiment ledger, successor back-link, or scope carrier to this topology
Change.

Alternative rejected: storing relationships in a docs index, registry, or
mutable lifecycle state. That would turn projections into authority.

### 4. Move in one closure-preserving batch

Build a repository panorama first, then update the selected owner and all
consumers in one admitted batch. The batch includes imports, tests, docs links,
stable paths, taxonomy, registry fixtures, generated projection inputs, and
OpenSpec references. After deletion, search the whole repository and run the
existing import, docs, architecture, and projection checks before broader
proof.

## Risks / Trade-offs

- [Risk] Flattening breaks a package boundary -> inspect public imports, child
  packages, resources, and registration consumers before moving.
- [Risk] Moving quickstart leaves stale references -> run repository-wide path
  closure and Docs Registry validation on the same tree.
- [Risk] Removing README loses navigation -> require a concrete index or
  boundary consumer and absorb unique links before deletion.
- [Risk] History is mistaken for current ownership -> classify Git and archived
  OpenSpec history structurally; historical text never authorizes behavior.

## Migration Plan

1. Inventory source, docs, rules, skills, OpenSpec, configuration, tests, and
   generated projection relations from one frozen HEAD.
2. Classify each package, README, and docs root by owner, consumers, boundary,
   and reason to change; create RED only for proven violations.
3. Apply the smallest batch of owner moves, consumer rewrites, and deletions.
4. Run repository-wide reference/import/link/projection closure and focused
   quality checks; stop on the first unknown or duplicate owner.
5. Run exact-HEAD full proof after the batch freezes. Archive, reprove, land,
   close out, publish, and retire through the public lifecycle; those effects
   remain evidenced by existing receipts rather than this task list.
