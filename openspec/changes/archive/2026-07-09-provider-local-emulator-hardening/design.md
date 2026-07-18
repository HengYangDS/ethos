# Design

The emulator evidence remains local provider-emulator evidence. It records the
provider projection and materialization boundary rather than claiming hosted
provider success.

For both providers, the evidence envelope records:

- provider, mode, command, tool availability, and return code;
- template, projected provider file, and emulator config existence plus digests;
- Git start and end summaries, including head, dirty state, staged paths,
  unstaged paths, and an untracked preview;
- `head_stable`, which must be true for the evidence to be ok;
- materialization policy: normal run modes refuse untracked files by default;
- hosted GitHub and GitLab status booleans set to false.

Dry-run, doctor, list, and dry-run modes are allowed to inspect even with
untracked files because they are non-proof discovery modes. Normal run mode can
be overridden for exploratory work with `ETHOS_LOCAL_EMULATOR_ALLOW_UNTRACKED=1`,
but that override is recorded in the evidence and remains local-only.
