## Context

See `proposal.md` for motivation and `specs/quality/spec.md` for the required
behavior. The repository already has one actionlint policy, one checksum-bound
tool declaration, and one owner script. Hosted GitHub and GitLab projections
already invoke that script, but `system/gates.toml` does not expose it to the
canonical full proof graph. The accepted GitHub projection also places
`runner.temp` in job-level `env`, where GitHub's expression grammar does not
admit the `runner` context.

## Goals / Non-Goals

**Goals:**

- Reuse the existing actionlint owner as one declared full-proof gate.
- Keep the template and generated GitHub workflow byte-equivalent.
- Move the Python installation root to a legal job-level expression under the
  repository's existing ignored `build/runtime/**` lifecycle.
- Prove gate selection, command identity, and projection semantics with one
  focused architecture regression.

**Non-Goals:**

- Claim hosted-provider success from a local syntax check.
- Redesign actionlint acquisition, the broader quality graph, or foreign quality
  work.
- Add a wrapper, registry, cache authority, compatibility path, or persistent
  state.

## Decisions

### Reuse the existing actionlint owner

Add one `github-workflow-syntax` gate whose command is the existing
`tools/ci/scripts/run-actionlint.sh`. Select it exactly once in the canonical
full proof after `config-quality`. This makes `system/gates.toml` the only gate
declaration while retaining `.config/checks/github/actionlint.toml` as the
tool-version and checksum owner and the script as the executable adapter.

The gate truthfully declares `writes_files = true` because a cache miss may
materialize the checksum-verified tool under `build/runtime/**`, and
`network_policy = "required"` because that existing supply path may download the
archive. The semantic validation itself remains deterministic. Splitting tool
acquisition into another gate or installer is rejected because it adds an owner
without being necessary to close this syntax-proof gap.

### Use a legal repository-owned Python supply root

Set job-level `UV_PYTHON_INSTALL_DIR` to
`${{ github.workspace }}/build/runtime/python` in the canonical template and its
generated workflow. `github.workspace` is legal at that scope and the path stays
inside the repository's existing generated-runtime boundary. Repeating
`runner.temp` at individual steps is rejected because it duplicates one
coordinate and leaves the job-level projection structurally inconsistent.

### Bind the projection and proof graph in one regression

Extend the existing CI provider projection architecture test rather than create
a new test module. It will assert the legal Python supply coordinate, exact
template projection, one full-proof selection, and exact owner command. The
real owner script supplies the behavioral RED/GREEN check against actionlint.

## Risks / Trade-offs

- **The existing owner may fetch actionlint on a cache miss.** → Preserve its
  checksum and version authority and declare the gate's network/write behavior
  honestly; supply redesign belongs to the later assurance/supply batch.
- **A local syntax pass could be mistaken for hosted success.** → Keep the gate
  evidence class distinct from hosted provider observations and state the
  separation in the quality requirement.
- **Template and projection may drift.** → Modify both in one atom and retain the
  existing `ci_templates` equality gate.

## Migration Plan

1. Add and observe the focused architecture regression fail because the gate is
   absent and the job-level expression uses `runner.temp`.
2. Add the existing owner command to `system/gates.toml` and full proof exactly
   once; update the template and generated workflow together.
3. Run the focused regression, actionlint, template projection, gate contracts,
   configuration quality, and strict OpenSpec validation.
4. Complete exact-HEAD proof, archive/reproof, candidate/accepted CAS, remote
   projection, and hosted observation through the normal public lifecycle.

Rollback is the exact inverse Git transition before publication. After
publication, rollback requires a new proved descendant; no in-place mutation or
compatibility path is retained.
