## Why

At accepted commit `82cf943a`, GitLab verification failed because an emulator test accidentally consulted host Docker, and the security job failed when `pip-audit` lost its remote transport before producing JSON. Neither result represents a product defect or vulnerability finding.

## What Changes

- Isolate the materialization fixture from Docker discovery.
- Retry one classified transient `pip-audit` transport failure.
- Preserve final failure for vulnerabilities, malformed JSON, and unclassified errors.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: subject=hosted-ci-remediation; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=ci,test,openspec,evidence; facet:authority=source,test,openspec,claim,evidence.

## Out Of Scope

- Workflow, dependency, credential, provider-topology, historical-pipeline, and foreign-lane changes.
- Retrying vulnerabilities, malformed JSON, or unclassified scanner failures.

## Impact

The existing owner script, two existing architecture test modules, the quality requirement, a bounded source-budget debt record, and one active carrier change. No new runtime tool or workflow is added.
