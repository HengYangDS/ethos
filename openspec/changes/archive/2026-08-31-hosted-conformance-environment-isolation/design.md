## Context

The repaired Windows trust-anchor path completed successfully in Hosted
conformance. The next tests then failed before `git init` because
`GIT_CONFIG_COUNT=3` and `GIT_CONFIG_KEY_0=credential.helper` survived while the
empty `GIT_CONFIG_VALUE_0` did not. Separately, the Linux verify job failed while
configuring the governed checkout because its minimal image did not contain
`ssh-keygen`.

## Goals / Non-Goals

**Goals:**

- Keep every indexed Git configuration entry complete on all supported hosts.
- Retain isolation from user and system Git configuration.
- Supply the native signing tool before the existing checkout configuration
  script uses it.

**Non-Goals:**

- No change to the Windows ACL algorithm, Git signing policy, hook/runtime
  lifecycle, publication model, or adopter repositories.
- No shell fallback, synthetic key generator, retry, or provider-specific test
  branch.

## Decisions

Delete the redundant empty `credential.helper` indexed entry from the pytest
overlay. `GIT_CONFIG_GLOBAL` already points to the null device,
`GIT_CONFIG_NOSYSTEM=1` hides system configuration, and
`GIT_TERMINAL_PROMPT=0` prevents interactive credential acquisition. The two
remaining indexed entries retain the fixture's repository semantics without an
empty value crossing the Windows process environment boundary.

Extend the existing Linux prerequisite list in `bootstrap-python.sh` with
`openssh-client` when `ssh-keygen` is unavailable. The bootstrap remains the
single owner of host package acquisition and still installs only observed
missing prerequisites.

## Risks / Trade-offs

- Removing the explicit empty credential helper relies on the fixture's already
  stronger global/system configuration isolation and disabled prompting.
- Linux package naming is intentionally scoped to the existing Debian-family
  bootstrap selected by the pinned hosted image.
