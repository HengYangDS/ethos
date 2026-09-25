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

Preview touches no destination. Apply checks parent/path safety, exact plan
identity and target absence immediately before effect. Exclusive target
creation is preferable to a rename that could replace a concurrently created
empty directory. Copy, runtime activation and post-observation are separate
effects: a failure after target creation reports confirmed bytes and UNKNOWN
remainder, never a false atomic rollback. Normal staging cleanup is mandatory;
crash residue needs owner/liveness-based bounded recovery before shipping.

### Let domain generators propose, not govern

The foundation is language-neutral. A selected domain starter runs in the
same isolated candidate boundary with pinned source and inputs; its output is
reviewed under the same digest and path-safety contract. Use the domain's
native generator when it is the owner of that layout. For a template that must
evolve with project customization, use Copier's versioned three-way update
instead of implementing another merge algorithm. Keep executable template
tasks disabled unless separately trusted. Its native answer/source metadata
is upgrade input, not ETHOS intent or proof. An upgrade yields a candidate
subject to normal repository admission; conflicts remain unapplied.

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
