## Why

GitHub main ETHOS CI run `30163837735` evaluated commit
`80272b76c22f4fd3964f4d936b4cfa0017a7426a`. In the repository-proof job, the
explicit `Unit and architecture tests` step passed, then
`tools/ci/scripts/run-head-bound-proof.sh` invoked `ethos prove --execute`, whose
default graph executed the same unit-and-architecture gate again. The duplicate
run failed on three unrelated exact 300-second timeouts after the same HEAD had
already passed the first full suite.

The workflow therefore doubles the most expensive and contention-sensitive gate
without adding an independent trust boundary. Removing only the redundant direct
invocation preserves the HEAD-bound proof, its digest, its 21-gate graph, JUnit
and coverage evidence, and the existing two-worker timeout policy.

## What Changes

- Make the GitHub repository-proof job execute the full test graph exactly once,
  through `tools/ci/scripts/run-head-bound-proof.sh`.
- Remove the preceding direct `tools/ci/scripts/run-python-tests.sh` step from the
  canonical GitHub template and generated workflow.
- Remove that script from GitHub's direct provider-script inventory while keeping
  it in GitLab and in the proof gate registry.
- Add an architecture contract that rejects a GitHub verify job containing both
  the direct test runner and the HEAD-bound proof runner.
- Add a quality capability requirement for one full hosted proof graph per job.
- Preserve GitHub's two workers, 300-second signal timeout, proof artifact upload,
  GitLab projection, and repository-wide test defaults.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: subject=github-single-head-bound-proof; reuse=extend; change=modify;
  facet:lifecycle=validation; facet:surface=ci,test,openspec,evidence;
  facet:authority=source,test,openspec,claim,evidence.

## Out Of Scope

- Reusing an earlier standalone pytest receipt inside `ethos prove`.
- Adding a global host lock or changing foreign Work Lane scheduling.
- Changing `run-head-bound-proof.sh`, the proof gate registry, timeout values,
  worker count, individual test limits, or automatic retry behavior.
- Changing, probing, pushing, or otherwise observing GitLab while outside the
  intranet.
- Treating a failed hosted run as successful.

## Impact

The canonical GitHub Actions template, its generated workflow, GitHub's direct
owner-script inventory, one provider architecture test, a quality OpenSpec
requirement, bounded Claim/Chronicle evidence, and generic parity evidence. No
product runtime, dependency, GitLab, proof-command, test-policy, or runner-label
change.
