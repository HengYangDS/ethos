## Context

The common Git directory already stores content-addressed wheels, immutable
runtime directories, runtime manifests, and content-addressed hook launcher
generations. The manifest validates the Python executable and ETHOS entrypoint,
but schema 1 identifies a runtime only by wheel hash, ABI, and platform. Nothing
links that valid wheel to the accepted ETHOS source that currently owns hook
semantics.

## Goals / Non-Goals

**Goals:**

- Make source currentness part of the existing immutable runtime identity.
- Preserve package-only and offline hook installation.
- Use the accepted ETHOS Git ref as the self-hosted expectation and packaged
  wheel provenance as the adopter expectation.
- Make every consumer observe one typed binding, one stable gap, and one exact
  repair action.
- Delete the integrity-only manifest assumption without adding a registry or
  mutable current-generation pointer.

**Non-Goals:**

- Runtime generation retention, garbage collection, SemVer, release provenance,
  SBOM, dependency upgrades, or additional Git hooks.
- Lease recovery, Commitment scope expansion, maintainer break-glass, or adopter
  repository changes.
- Treating a source path, active process, or host-local package cache as authority.

## Decisions

### Build identity is immutable wheel data

Extend the existing Hatch build hook to force-include one small canonical JSON
resource containing `source_commit` and `source_tree`. Runtime installation
reads this resource through `importlib.resources`; a package-only install never
needs the original checkout. The runtime digest includes the source identity, so
two source identities cannot share a runtime directory even if other inputs are
equal.

Alternative rejected: infer source from package version or an absolute build
path. Neither identifies exact repository bytes and both decay after relocation.

### Expected identity depends on the truthful execution context

When the runner source belongs to the audited ETHOS repository family, resolve
the accepted branch and its linked worktree, then use the accepted ref's exact
commit and tree. Otherwise use the invoking installed wheel's packaged build
identity. This keeps adopters source-independent while preventing a Work Lane or
candidate build from silently becoming accepted hook authority.

Alternative rejected: compare against the current checkout HEAD. A Work Lane
HEAD is a candidate implementation, not accepted hook policy.

### One forward-only runtime manifest

Promote the existing manifest to schema 2 and include source commit/tree in its
digest and validation. Schema 1 remains historical bytes but is non-current and
routes to repair. There is no dual reader, alias, fallback, or migration database.

### Runtime binding owns diagnosis and repair projection

The hook binding reports installed and expected identities, currentness state,
required gaps, and one repair action. Existing status, admission, Git effect, and
lifecycle consumers continue to depend on `required_gaps`; they do not invent
their own stale-runtime policies. Hook installation post-observes that same
binding and reports success only when it is current.

The self-hosted repair action runs the accepted checkout's source-bound command
against the exact audited worktree. The package-only action uses the invoking
wheel command. Paths are shell-quoted and fully bound; no placeholder command is
emitted.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| `distribution:Package-only hook runtime carries accepted source identity` | `2.1` | isolated-wheel build identity and install smoke |
| `repository-governance:Hook runtime currentness is mutation admission` | `2.3` | stale intact runtime regression and existing mutation consumers |
| `command-plane:Hook runtime inspection exposes one exact repair action` | `2.5` | binding/status projection and repair black-box regression |

## Risks / Trade-offs

- [Risk] A wheel is built from the wrong checkout → Mitigation: carry exact
  commit/tree and compare it with accepted source before activation.
- [Risk] An adopter has no ETHOS source checkout → Mitigation: package the same
  identity in the wheel and use it as the package-only expectation.
- [Risk] A stale runtime blocks its own repair → Mitigation: the repair command
  is projected by the current reader and uses the existing source/package
  installation path, not the stale hook executable.
- [Trade-off] Historical schema-1 runtimes become immediately non-current. This
  is intentional forward-only convergence; the public repair path replaces the
  projection without deleting referenced generations.

## Migration Plan

1. Add RED cases for an intact old runtime and its exact repair action.
2. Package and validate source identity through the existing build/runtime owners.
3. Promote the manifest and binding forward-only; remove schema-1 authorization.
4. Post-verify install, package-only smoke, mutation consumers, and lifecycle recovery.
5. Run strict OpenSpec, static/architecture gates, full proof, archive, and land.

## Open Questions

None. Retention and release provenance remain dependency-linked successor work.
