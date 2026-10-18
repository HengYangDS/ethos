# Proposal

## Why

`repository-paradigm` keeps three compatibility obligations that only an adopter's own migration can release: the docs registry still reads comment-wrapped metadata because data-department-work-guidelines tracks such documents, and the legacy role rename, its Git admission and the legacy role ref retirement remain because di-effect still declares legacy role names, and its migration stays deferred. Waiting for them would keep `repository-paradigm` unarchived. This Change carries tasks 2.16, 2.21 and 2.19 until those adopters release them.

## What Changes

- Continue the listed tasks with their original identities, states, acceptance conditions and dependencies, moved verbatim.
- Add no requirement. `repository-paradigm` accepts the requirements these tasks implement, including the documentation metadata scenario that reads a comment-wrapped document as missing metadata.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- None. The behavior these tasks implement is specified by the specifications that `repository-paradigm` accepts.

## Impact

The docs registry and the legacy role migration code, their tests and the documentation that describes them. Each task waits on its adopter: 2.16 on data-department-work-guidelines, 2.21 and 2.19 on di-effect. Original execution history remains in Git and in the design of `repository-paradigm`.
