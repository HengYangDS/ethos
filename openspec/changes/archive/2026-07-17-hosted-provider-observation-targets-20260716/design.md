# Hosted Observation And Report Closure Design

## Context

The observation envelope is provider-neutral, but each provider CLI currently
discovers its repository from the Git origin remote. The ETHOS repository has a
GitLab SSH remote whose host spelling differs from the authenticated API host
and no GitHub remote. Both provider CLIs are installed, so execute mode records
two lookup failures even though GitLab pipelines exist and GitHub is simply not
configured.

Repository identifiers must remain runtime configuration. Committing the
current private project path would violate the enterprise-neutral product
boundary, while continuing remote inference would keep the observation
nondeterministic.

The completion audit also requires report to distinguish local publication and
hosted observation state. Those are read-only projections: neither may become
proof, hosted success, or remote-publication authority.

## Goals / Non-Goals

**Goals:**

- Bind every provider command to an explicit runtime repository target.
- Distinguish provider-not-configured from command execution failure.
- Preserve exact command, target source, provider output, and normalized facts
  in the observation envelope.
- Summarize bounded provider observation gaps without converting them into
  repository proof gaps.
- Project current local publication readiness and hosted observation
  freshness/state through ethos report.
- Keep observation, proof, hosted status, and publication evidence separate.

**Non-Goals:**

- Configure provider credentials, remotes, project settings, or branch rules.
- Require both providers to be configured.
- Turn a successful provider response into an ETHOS proof or publication claim.
- Add a provider SDK or a second observation command plane.
- Make report perform a remote probe or a publication transition.

## Decisions

### Tracked configuration names runtime target variables

The hosted observation TOML keeps the ordered provider list and adds one
repository-target environment-variable name per provider. GitHub uses
ETHOS_HOSTED_GITHUB_REPO and GitLab uses ETHOS_HOSTED_GITLAB_REPO. Only the
variable names are committed; repository identifiers remain runtime state.

This is preferred over hard-coded targets because the product must remain
portable, and over Git remote inference because authenticated provider hosts and
Git transport hosts need not have identical spellings.

### Execute mode is target-gated

Command construction accepts the resolved repository target and always adds the
provider-native --repo selector. If the target variable is empty, the runner
does not invoke the provider CLI and records not_configured with executed=false.
If a target exists but the CLI is absent, tool_unavailable remains the bounded
state. A configured command that returns non-zero remains observation_failed.

This ordering distinguishes absent intent from missing tooling and from an
actual provider response failure.

### Envelope state is derived from provider states

Dry-run remains dry_run. Execute mode is observed when every configured
provider succeeds, partial when at least one provider succeeds and another is
not configured or fails, not_configured when no provider target exists, and
observation_failed when configured providers were attempted but none succeeds.
The envelope lists stable observation gap codes. Those gaps describe provider
observation completeness and do not enter repository proof required_gaps.

### Report reads generated evidence without promoting it

A repository evidence reader loads the configured observation artifact, checks
its head against the current tracked head, and returns missing, invalid, stale,
or current status plus provider-state summaries. Report includes that object
under hosted_observation and adds its bounded gaps to advisory signals only.

Report also includes a local_publication object derived from its current
blocking gaps and proof readiness. It is explicitly a read-only scorecard
projection with remote_publication_claimed=false and does not replace the
publish transition verdict.

### The envelope records targeting without minting authority

Each provider record includes target_env, target, target_configured, command,
tool availability, execution state, return code, raw previews, and normalized
facts. The top-level hosted GitHub status, hosted GitLab status, and remote
publication claim flags remain false in every path.

## Risks / Trade-offs

- A malformed runtime target can still make a provider CLI fail. The exact
  command and stderr remain captured so the failure is diagnosable.
- Repository targets appear in ignored build evidence. This is required for a
  reproducible observation but does not promote them into tracked product
  defaults.
- Existing execute invocations without target variables change from misleading
  provider failures to not_configured. This is an intentional semantic repair.
- Missing or stale observation evidence makes report advisory rather than
  blocking. This preserves the provider evidence boundary while keeping the
  incompleteness visible.

## Migration Plan

1. Add failing tests for explicit --repo arguments, aggregate states, report
   projection, and unconfigured-provider non-execution.
2. Add the target-variable policy to the hosted observation configuration.
3. Implement target-gated command construction and derived observation gaps.
4. Add the observation evidence reader and report projections.
5. Run focused tests, config lint, local provider emulators, and an executed
   local GitLab observation with an explicit target.
6. Archive the OpenSpec change, bind the claim, and run HEAD-bound proof.

Rollback is a normal revert of the configuration, implementation, tests, and
spec deltas. No provider-side state is mutated by either migration or rollback.

## Open Questions

None.
