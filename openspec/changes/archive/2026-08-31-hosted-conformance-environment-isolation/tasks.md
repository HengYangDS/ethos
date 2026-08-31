## 1. Preserve the hosted failures

- [x] 1.1 Add a regression requiring complete, non-empty indexed Git
  configuration values in the host-conformance test environment.
- [x] 1.2 Add a regression requiring the Linux bootstrap to supply
  `ssh-keygen` through its native prerequisite package.

## 2. Repair the unique owners

- [x] 2.1 Delete the redundant empty credential-helper overlay while preserving
  Git isolation and prompt suppression.
- [x] 2.2 Extend the shared Linux prerequisite bootstrap for the existing signing
  workflow and pass focused validation.
