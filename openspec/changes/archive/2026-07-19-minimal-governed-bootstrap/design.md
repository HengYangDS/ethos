## Context

The current compiler owns 47 templates plus a 378-line manifest, 300 lines of
compiler/model code, and roughly 700 lines of direct scaffold tests. It emits
66 files and about 1,400 physical lines for a generic adopter. Most outputs are
empty homes, generic documentation, predeclared decision indexes, copied skill
packages, or speculative capability records. They do not bind adopter identity
and are not read by the default adoption decision.

The existing runtime already treats `.ethos/profile.toml` as the adopter
binding manifest. Its defaults cover standard roots and branch roles; the
profile's `[openspec].material_paths` declaration is the only bootstrap content
needed to make subsequent governed writes fail closed.

## Goals / Non-Goals

**Goals:**

- Reduce default adoption from 66/67 files to one binding manifest, unless a
  later focused test proves another file indispensable.
- Delete the manifest, family/skill declarations, optional templates, `.gitkeep`
  outputs, provider templates, package-digest machinery, and tests that only
  preserve the old byte set.
- Preserve typed, strict rendering for the surviving text leaf.
- Preserve default read-only planning, apply, conflict refusal, binding detection, and rollback
  reporting over the smaller output set.
- Make later docs, OpenSpec, skill, release, and provider creation explicit
  commands owned by those capabilities rather than implicit adoption side
  effects.

**Non-Goals:**

- No migration or update of repositories already adopted.
- No compatibility aliases, legacy output mode, full-scaffold profile, or
  dual-run.
- No new scaffold framework, code generator, answer/state file, or generated
  Python.
- No claim that the minimal profile alone proves code correctness or hosted CI.

## Decisions

1. **One binding carrier.** Default adoption writes only
   `.ethos/profile.toml`. Repository name, default roots, branch roles and
   absent optional policy already have runtime defaults; copying those defaults
   into separate files adds truth surfaces without adding behavior.
2. **No template for typed TOML.** The old output-path/template-path manifest,
   renderer taxonomy, and packaged template are deleted. `tomli-w` serializes
   the strict declaration directly.
3. **Interpret first, generate last.** Profile facts are interpreted at runtime.
   Text generation remains only for the unavoidable tracked binding leaf. No
   documentation, schema, skill, test, or business source is generated.
4. **Lazy capability creation.** OpenSpec workspace initialization remains the
   official OpenSpec command's concern. Skills, hosted CI and docs topology are
   explicit later projections. Adoption does not reserve their directories.
5. **No automatic update lineage.** Copier, Cookiecutter, Cruft and Projen are
   rejected because ETHOS does not promise downstream template rebasing. Git
   history records the old scaffold; active code carries only the terminal
   bootstrap.
6. **Behavior tests, not byte snapshots.** Tests assert the recognized-adopter
   invariant, exact one-file plan, strict conflict semantics, typed render
   validation, and wheel inclusion. Digest snapshots and complete skeleton
   assertions are deleted.
7. **Quality is native to each surviving carrier.** Ruff/ty/pytest cover Python;
   Taplo and strict profile parsing cover TOML. Retired Jinja carrier, metric,
   formatter, and whitespace ownership are deleted rather than left empty.
8. **Optional capability absence is inert.** A valid adopter with no matching
   material change and no explicitly selected capability does not acquire gaps
   for absent docs, claims, skills, schemas, generated artifacts, hosted
   providers, or OpenSpec workspace. Native correctness remains separately
   fail-closed.

## Risks / Trade-offs

- **Default adopter proof currently selects gates that assume precreated docs,
  OpenSpec and auxiliary config.** The gate selection and requirements must be
  reconciled so bootstrap recognition is distinct from later capability
  readiness; missing optional surfaces remain explicit gaps only when their
  capability is invoked.
- **Existing tests encode the old skeleton as product behavior.** Replace only
  owner tests; do not add a parallel minimal test suite while retaining the old
  one.
- **Users may expect GitHub/GitLab files from adoption.** Provider projection is
  a separate explicit operation. No hidden provider file is written during adoption.
- **A hidden runtime consumer may read a deleted output.** Repository-wide
  reference search plus focused adopter status/plan/prove tests must demonstrate
  the actual dependency before deletion.

## Migration Plan

1. Add failing tests for an exact one-file bootstrap and recognized adopter.
2. Collapse the planner to one typed declaration and native TOML serializer.
3. Delete all unused templates, manifest records, declarations and digest logic.
4. Delete or rewrite old scaffold tests and capability assertions.
5. Reconcile adopter readiness checks with lazy capability creation.
6. Run focused tests, Ruff, ty, Taplo/config checks, strict OpenSpec validation,
   Ponytail review, source-budget measurement and HEAD-bound proof.
7. Let official OpenSpec archive update canonical requirements, then locally
   close the Change; do not push during the Campaign.

## Open Questions

None. Any second default output must be justified by a failing runtime invariant,
not by symmetry or future convenience.
