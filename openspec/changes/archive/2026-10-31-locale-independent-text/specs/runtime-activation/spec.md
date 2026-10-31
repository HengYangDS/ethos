## MODIFIED Requirements

### Requirement: Runtime image preserves native execution identity

Construction SHALL preserve standalone native layout and compare paths by native identity so the
generated executable reports its image as sys.prefix and sys.base_prefix. Authenticated Python with
`-B -I -X utf8 -m ethos.cli` SHALL be the sole internal ETHOS execution authority, and one product
owner SHALL name those interpreter flags for every Python process ETHOS starts. Generated console
scripts SHALL NOT define runtime identity, currentness or internal execution.

#### Scenario: A Windows standalone interpreter is materialized

- **WHEN** runtime activation copies an admitted Windows CPython image source
- **THEN** `python.exe`, `Lib`, `DLLs`, and native runtime DLLs retain their platform-relative
  layout
- **AND** executing the copy reports a path-identical generated image root as both `sys.prefix` and
  `sys.base_prefix`, regardless of equivalent Windows separator or case spelling
- **AND** runtime post-observation and selected-runtime continuations execute
  `python.exe -B -I -X utf8 -m ethos.cli`
- **AND** relocating the generation does not depend on `Scripts/ethos.exe`.

#### Scenario: Runtime module execution fails

- **WHEN** the authenticated runtime Python cannot execute `ethos.cli`
- **THEN** activation fails before selector mutation
- **AND** evidence identifies the exact command, return code, stdout, and stderr.

#### Scenario: ETHOS runs on a host whose locale is not UTF-8

- **WHEN** ETHOS starts its runtime Python, a release console launcher starts it, or ETHOS starts
  supply Python
- **THEN** that process runs in Python's UTF-8 mode
- **AND** its default file, standard-stream and pipe encoding is UTF-8.

### Requirement: Runtime discovery uses locked offline native tooling

Construction SHALL NOT install Python, access networks, require uv-managed provenance or persistent
caches. Use <supply-python> -B -I -X utf8 -m uv, never a guessed sibling binary. Only if the base
lacks image capability MAY this boundary list installed candidates, with downloads, network, cache
writes and project config disabled. Selection SHALL be deterministic by identity and image
capability.

#### Scenario: An incapable base triggers bounded discovery

- **WHEN** the reported base cannot supply a native image
- **THEN** discovery invokes locked uv through supply Python and lists only installed candidates
- **AND** no network, download, cache-write or project-configuration effect is enabled
- **AND** the same identity and image-capability checks determine selection.
