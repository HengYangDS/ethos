# Tasks

## 1. Transport Failure Recovery

- [x] 1.1 Classify npm's audit error object whose message names the bulk advisory request as `advisory_request_failed`; verify a malformed report and a report with findings keep their existing reasons.
- [x] 1.2 Repeat only an `advisory_request_failed` npm observation, at most three attempts within the policy timeout, and record every attempt in the receipt; verify a failure followed by a clean result passes with both attempts recorded, three failures fail with three attempts, and findings are observed once.

## Workflow follow-up

- Prove the exact head, archive this Change, prove the archived head, then land, close out and publish.
