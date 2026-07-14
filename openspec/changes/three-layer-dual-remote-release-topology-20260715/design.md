## Context

ETHOS already separates local proof, remote reachability, remote publication,
and hosted-provider observations. It currently models one implicit remote.
That cannot express a GitLab-primary organization that keeps GitHub as an
independent distribution mirror.

## Design

The release policy declares three roles:

1. **Local**: verification and installation; it is remote-independent.
2. **Primary**: GitLab through the configured `origin`; it alone represents
   organizational primary publication.
3. **Mirror**: GitHub through the configured `github` remote; when GitLab is
   unavailable, it may substitute only for update and distribution.

`ethos publish` remains read-only. It independently probes or labels both
remotes, emits a topology projection, and never changes `remote_push` from
`not_performed`. Its projection uses explicit false claim flags so a GitHub
observation cannot be reinterpreted as GitLab success.

## Proof Strategy

- Unit tests cover the declared release topology and missing mirror surfaces.
- Publish tests cover GitLab-primary / GitHub-mirror fallback semantics and
  continue to assert no remote publication claim.
- Focused lint, OpenSpec validation, and HEAD-bound proof run in the owned lane.
