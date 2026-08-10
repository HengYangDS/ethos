# Design

## Decision

`[publication]` retains the two local command owners and contains zero or more
`[[publication.peers]]` tables. A peer has `id`, `provider`, `role`,
`git_remote`, and `capabilities`; `ci_surface` is optional unless `ci_cd` is in
`capabilities`.

The compiler produces one ordered `remotes` collection and no provider-named
top-level aliases. Every consumer iterates that collection. Peer ID, provider,
and Git remote are individually unique so observations remain unambiguous.
Unknown declaration fields and any retired fixed-provider scalar fail closed.

An empty peer collection is the explicit local-only topology. The local
verification and installation commands remain mandatory because they
are repository-owned correctness and package acceptance contracts independent
of hosted peers. A repository-only GitLab peer therefore proves local quality
and remote reachability without claiming hosted CI.

Hook installation may remove the legacy common-directory
`ethos-runtime-python` file or symlink only after the final immutable runtime,
manifest, public entrypoint, and hook launchers pass validation. Cleanup is
reported as an explicit disposition and never supplies runtime authority.

## Authority boundaries

- The release declaration owns which peers exist.
- Git observations report facts for declared remotes only.
- Branch admission grants no authority to undeclared remotes.
- Optional CI absence never becomes positive hosted-CI evidence.
- Package-only hook runtime and canonical SQLite remain the execution and state
  authorities after legacy-locator retirement.

## Migration

This is a breaking cutover. Existing repositories must replace
`gitlab_remote`, `github_remote`, and provider-specific CI scalars with peer
tables. There is no compatibility reader or implicit default peer.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| `repository-governance:publication topology is declared, not inferred` | `1.1` | `unit-publication-topology` |
| `repository-governance:hosted CI claims follow declared capabilities` | `1.2` | `unit-publication-readiness` |
| `distribution:hook installation retires the legacy runtime locator` | `2.1` | `unit-hook-runtime` |
