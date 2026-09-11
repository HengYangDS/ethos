## Context

See proposal.md for motivation. Existing CEL owns placement; native projection
declarations own source/output relations; Git supplies exact preimages and patch
postimages. Format ownership governs serialization, not generation provenance.

## Goals / Non-Goals

Preserve ordinary authoring, producer-owned projections, exact deletion scope and
surviving consumers through one admission path. Do not turn file names, Git
tracking, or a missing path into evidence that an artifact was generated.
Unknown dynamic consumers are not a claim of complete program analysis.

## Decisions

1. Remove the suffix classifier and its source-filename exceptions. The topology
   contract accepts observed generation facts; absent origin is unclassified.
   Existing lifecycle homes identify runtime ownership. Existing native
   architecture and CI declarations identify projection ownership and placement.
   A declaration names an output relationship, not a second source of intent.
2. Keep one native projection observation owner. Existing CI template and diagram
   validators consume its source/output relations and preserve their rendering
   checks. A formatter label cannot make a source model a generated output.
   Manual generated-output edits require an exact patch checked against their
   current native producer; generation cannot be authorized by a caller label.
3. The Git pre-commit transport selects the exact index tree, not current
   working bytes. It shares producer/deletion evaluation with patch admission;
   baseline and final HEAD/index observations reject changed coordinates,
   including drift during later scope checks. Staged paths and existence come
   from Git, not symlink resolution in the unstaged working copy. The public
   request binding includes the observed index tree.
   Git object reads reuse one batch reader with explicit caller error context.
4. Reuse the current patch materializer. It returns changed postimages and
   removed paths, builds the effective source view, and checks affected native
   consumers. Removal of an output is valid only after its producer relation is
   removed or redirected coherently. Removing authored configuration with its
   consumers is ordinary authoring, not a generation-policy exception.
5. Public output separates path containment, placement, ownership, existence and
   effect. A missing patch for a producer-owned output requests exact patch
   admission. Invalid declaration or unsupported required observation is unknown;
   known drift or surviving required input is blocked. No blind mutation retry.
6. An exact patch can repair invalid uncommitted producer syntax. Preserve known
   committed owners and parse the full effective successor declarations before
   allowing that repair. Invalid unchanged declarations remain unknown. Producer
   effect evaluation runs once over the combined prior relations, not through a
   second duplicate validation path.

## Risks / Trade-offs

- Native input interpretation is bounded: consume explicit supported native
  configuration and command options, not arbitrary prose or string occurrence.
  Tests distinguish true inputs, output/echo mentions and dynamic unknowns.
- Projection declaration edits are candidate source: compare preimage and
  postimage relations so deleting a declaration alone cannot disguise an output
  as ordinary authoring. Exact policy, source and patch remain bound to admission.
- Package and source readers must share the same owner. Promote existing pure
  render logic where needed and remove its superseded implementation rather than
  importing repository tools into installed product code.

## Migration

Update the sole topology declaration and all consumers together. Retain existing
native projection carriers and generation commands; require no adopter carrier.
Verify ordinary source, generated projection, absent path and coherent deletion
through public admission, then full proof, official archive and accepted runtime.
Report the accepted package identity before offering the public adopter rebind.

### Predecessor Enforcement During Policy Migration

The current immutable runtime still parses the original topology declaration.
The successor removes suffix-classifier fields, so its working declaration is
not consumable by that predecessor. Passing source-runner admission does not
prove the installed Git hook can admit the same change. A normal commit must
remain governed; do not hide staged policy changes behind older working bytes,
change the installed runtime in place, disable hooks, or lower policy checks.

Treat runtime code and its executable generic policy as a coherent versioned
unit. Move the sole declaration beside its interpreter as
`src/ethos/contracts/artifacts/topology.toml`, using native package resource
loading in both source and wheel execution. Delete the old system carrier and
force-include mapping; remove caller-provided topology paths. Existing installed
predecessors then use their already-packaged policy when the old carrier is
absent. Successors never select topology policy from cwd or the audited root.
This is a removal of the conflicting authority, not a temporary schema shim.
Repository gate declarations retain their own distinct loading semantics.

Verify direct and public-gate isolation from incompatible checkout declarations,
and fail closed for missing or invalid package resources. Normal predecessor hook
execution and exact successor package proof are separate required observations.
Migration implementation tests belong in tasks; actual proof/archive/acceptance
and runtime activation remain delivery effects, not self-referential task gates.

### Prepared Quality Runtime

The first exact-source proof exposed a nested `uv run --offline` in the
configuration gate. It attempted editable-package bootstrap and failed on an
unavailable build-dependency cache before any heavy dependent tests ran. Native
Nox gates execute through the already-bound interpreter; provisioning remains
outside gate execution. Remove this lone nested bootstrap command rather than
warm an ambient cache to conceal a second environment owner. Regression checks
all declared Nox gates bind the same interpreter and preserve source identity.

### Source Measurement And Policy Compilation

The user's threshold review exposed a measurement defect before calibration:
whole-line string removal also erased neighboring code, and lexical comment
tests erased multiline literal data. Keep the existing pure measurement owner;
mask exact AST byte spans and count remaining token-bearing physical lines.
Python newline handling must preserve Unicode separators inside literal data.
Invalid syntax has no count. File and aggregate consumers use the same function.

Compile optional per-file policy through the existing rules parser and a strict
native model. Present limits are positive integer multiples of one hundred;
role omissions inherit an explicitly declared default, not a hidden runtime
ceiling. Absent policy is not configured for a generic repository. Present
malformed policy blocks; inaccessible input remains unknown. Neither condition
may become an empty passing measurement. Report the exact path, cause and fresh
prewrite derivation. Keep required-policy selection under repository governance;
the optional generic boundary does not authorize removing a required policy.

The current numeric declaration remains 500/500/800 while the user-requested
unified-500 trial evaluates the same accepted inventory. Existing sizes and
pass rate are diagnostics, not the justification for either ceiling. The trial
must examine semantic cohesion, duplicate setup and independent change reasons
without file splitting, role reassignment or evidence removal to fit a number.
Repository-wide consolidation is subsequent work, not silently added to this
artifact admission Change. Product/test aggregate budgets remain independent
45000 ceilings and combined coverage remains at least 95 percent.

The already-blocking proof surface repeats issuance payload fields and the
common compact/detailed response. Construct each once, keep bounded presentation
normalization separate from proof effects, and create a distinct failure payload
after persistence failure. Preserve public response fields and verdicts; remove
duplicate construction rather than moving it into a new module or weakening
the source ceiling. Existing persistence-failure and projection comparisons
must distinguish accidental mutation of an earlier observation.
