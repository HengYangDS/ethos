# Direct Closeout and GitHub Publication

## Why

The current campaign-terminal projection makes an active global compression
program a hard pre-push blocker even after a bounded Change has completed
executed local proof and accepted-root closeout. That couples long-horizon
terminal source reduction to every protected GitHub publication and contradicts
the approved GitHub-only direct-push path while GitLab is unavailable.

## What Changes

- Separate structural publication defects from campaign-progress advisories.
- Keep local proof, accepted closeout, remote branch policy, identity, and
  fast-forward topology as enforced protected-push requirements.
- Preserve campaign terminal state, source-budget settlement, and active debt
  as explicit advisory progress in the campaign publication report rather than
  a pre-push blocker for ordinary `dev` and `main` publication.
- Ensure the hook forwards the actual remote name to both admissions so a
  GitHub push is evaluated and reported as GitHub.
- Document GitHub-only operation as an explicit temporary remote-plane choice;
  it does not claim GitLab synchronization or hosted CI success.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=direct-closeout-github-publication;
  reuse=extend; change=modify; facet:lifecycle=closeout,publish,validation;
  facet:surface=cli,hook,docs,openspec,test; facet:authority=source,test,schema,docs,openspec,evidence.
- `quality`: subject=direct-closeout-github-publication; reuse=extend;
  change=modify; facet:lifecycle=quality,proof,release; facet:surface=policy,report,openspec,test; facet:authority=source,test,schema,docs,openspec,evidence.

## Impact

Affected surfaces are the declarative campaign publication policy, its typed
contract/schema, campaign report, pre-push adapter and CLI, regression tests,
and publication governance documentation. No remote is changed by this Change;
publication remains a separately observed and executed forge-plane action.

## Out Of Scope

- Closing the global compression campaign, settling its debt, or weakening full
  proof and terminal compression closeout requirements.
- Bypassing Git hooks, force-pushing, publishing `work/*` or `candidate/dev`,
  changing GitLab state, or asserting hosted CI success from local proof.
- Retiring foreign Work Lanes or deleting remote `submit/*` refs without their
  own accepted-ancestry observation and deletion dry-run.
