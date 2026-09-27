## Context

See the proposal for the missing product journey. In an isolated fresh Git
repository, current `adopt` successfully writes the profile and official
configuration; the next `status` still blocks on a missing candidate ref and
unarmed hook/runtime selection. That is correct for conservative brownfield
adoption but not a finished greenfield project. The installed-product Change
already owns portable package context; this Change consumes it rather than
building another runtime.

## Goals / Non-Goals

Form one usable repository without an ETHOS checkout, with a reviewed source
and output closure. Keep the existing `adopt` request byte-for-byte compatible.
The foundation does not dictate application language, CI provider, docs tree or
release policy. No generator may grant mutation permission or rewrite an
authored repository merely because it once produced a file.

## Decisions

### One onboarding owner, two explicit modes

Use `ethos adopt --create` for an absent destination; keep default `adopt` for
an existing Git repository. Both are typed application operations rendered by
CLI, SDK and MCP. This is clearer than treating a missing root as implicit
permission to initialize, and avoids another public command whose only shared
meaning is onboarding. Formation has a distinct precondition: target absence
and an exact candidate digest replace the existing-repository HEAD check.

### Compose native owners rather than copy their semantics

The foundation candidate supplies a purpose-bearing README and thin Agent
entry, then invokes the existing profile renderer, official OpenSpec config
owner and Git operations. Candidate construction uses a disposable directory
whose final component is the requested project name; this keeps profile
identity independent of the random staging parent. Generated input/output
digests exclude transient absolute paths. Preview exposes the physical target
after resolving its parent and binds both the requested alias and parent file
identity. Apply rechecks that binding and writes only to the physical target:
stable aliases such as macOS `/tmp` work, but a retargeted alias cannot move an
effect and an existing target link is refused. The initial commit uses the actual
author and committer selected by invocation flags or process-scoped Git
identity; their values enter the plan digest. Missing identity blocks before
publication. The foundation declares no signing requirement and does not
claim an unsigned commit is signed. Formation binds the policy-derived sibling
worktree path in the plan and refuses a collision before publishing the target.
After publication, the existing candidate bootstrap alone creates the
`candidate/dev` ref, worktree and shared hook/runtime activation from `dev`'s
initial object. A failed post-publication bootstrap is UNKNOWN, not permission
to repeat the effect. Status selects that bootstrap owner before a hook-only
repair when its worktree is missing; preview refuses a path collision before
another ref effect. The first Change is authored through official OpenSpec,
not a copied template.
An absent `openspec/specs` means no accepted capabilities yet, not a broken
repository. Native OpenSpec accepts a first ADDED Change; ETHOS validates a
specs root when present without requiring a placeholder directory or README.

Preview touches no destination. Apply checks parent/path safety, exact plan
identity and target absence immediately before effect. Exclusive target
creation is preferable to a rename that could replace a concurrently created
empty directory. Copy, runtime activation and post-observation are separate
effects: a failure after target creation reports confirmed bytes and UNKNOWN
remainder, never a false atomic rollback. Normal staging cleanup is mandatory;
crash residue needs owner/liveness-based bounded recovery before shipping.

### Let domain generators propose, not govern

The foundation is language-neutral. The first optional `python-library`
starter invokes the product's locked `uv` module in the disposable candidate,
offline and without ambient uv configuration, workspace discovery, VCS or
template tasks. Its selected package version and exact output bytes bind the
formation digest. Only exclusive regular files are admitted; links, junctions
and special files fail before the target exists. Unknown starter spellings do
not become generator arguments. A generated file cannot silently replace the
foundation's own output. The initial commit is bound to one result Attestation
holding the selected generator and exact starter path/digest subset; this is
upgrade provenance, not a second template manifest or rewrite authority.
Other domains retain their own native layout owners. A zero-exit generator
still needs the selected library output. For a later `uv` starter version,
bind a caller-reviewed old generated commit, the
current authored HEAD, and the new generator/version/outputs. Reuse the existing
quarantined Git-object merge mechanism, rather than writing another merge
algorithm or changing adopter files during preview. A clean object merge is a
candidate, not semantic acceptance; a conflict preserves authored bytes and
requires an explicit decision before normal repository admission.

The public `adopt --evolve-starter` path is preview-only. It reads the one
formation result from the existing Attestation Set, checks its repository and
initial Git object, verifies the recorded starter byte digests, and runs the
currently installed native generator in owned scratch. The original project
name comes from the recorded baseline's native `pyproject.toml`, not a Work Lane
directory name. It returns a Git merge patch or conflict without touching the
adopter. `--apply` is refused: review and effect admission belong to a current
owned Work Lane, not to generator provenance. The exact-patch lane admission
is covered by task 2.2; installed-product replay remains task 2.3.

Formation and starter-evolution tests exercise distinct public requests,
collisions, failure recovery, identity and authored-content preservation. This
candidate measures 55,697 test ELOC against the 55,000 aggregate ceiling.
Rather than delete those checks solely to fit the ceiling, raise only the test
aggregate to 60,000. Retain the 55,000 product ceiling, 500-per-file limit and
coverage floor; exact source-budget and full proof remain acceptance conditions.

For a missing repository, MCP requires explicit `--create-target` at startup.
It binds the requested alias and physical target, rejects retargeting on each
call, and keeps effect authorization in `adopt --create`. Ordinary MCP startup
still requires an existing root. An unborn Git root cannot supply a candidate
base; status and candidate operations report that missing fact before ref work.

Copier is not the update owner for this `uv` starter. Its documented update
path expects a Copier answers file and versioned Git template, and can run
migrations while writing conflicts into the destination. Adding those carriers
would duplicate the native `uv` layout and provenance. Projects already formed
from Copier templates may use that native capability through a separate
optional adapter, but it cannot become ETHOS intent or effect authority.
See [Copier 9.18.2 update semantics](https://github.com/copier-org/copier/blob/v9.18.2/docs/updating.md)
and [Git object-tree merge](https://github.com/git/git/blob/v2.55.0/Documentation/git-merge-tree.adoc).

## Risks / Trade-offs

- A large or unsafe starter can consume resources or escape its destination.
  Bound execution, reject symlink escapes and unpinned inputs, and test a
  hostile starter before admitting its adapter.
- Host-dependent Git identity, signature trust or missing OpenSpec supply can
  prevent formation. Detect these before publishing target bytes and report
  the exact missing prerequisite; never substitute an ETHOS author identity.
- Multi-file creation is not crash-atomic. Make effects and residue observable;
  do not replay after a lost acknowledgement without reading the target.
- More Agent adapters can multiply upkeep. Ship one package guidance source and
  only thin, tested entry projections for selected Agents.

## Migration Plan

Add the explicit creation mode without changing default adoption. Qualify the
foundation from a clean installed product, then one selected domain starter,
including customization and conflict. Only after fresh conformance, update
first-hour docs and package release. Existing repositories are not retrofitted
with generated files. Retire staging resources and any replaced guidance
projections only after their consumers are verified.
