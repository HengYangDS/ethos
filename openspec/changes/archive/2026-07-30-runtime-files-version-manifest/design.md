## Context

ETHOS already has a semantic product-root predicate and a strict adopter
profile. The release coupling adapter bypasses both by using the existence of
`pyproject.toml` as its discriminator. That physical shortcut leaks product
release assumptions into adopters and turns ordinary metadata diversity into
an uncaught `KeyError`.

Codex DMX Proxy is a runtime-files distribution. Its `pyproject.toml` is a
compact tool-owned policy carrier: `[tool.codex-dmx-proxy]` declares
`distribution = "runtime-files"` and `version-source = "VERSION"`. Adding a
fake `[project]` table would misrepresent both its packaging model and the
authority of `VERSION`.

## Decisions

### 1. Reuse semantic product-root detection

Generic coupling audits apply product release policy only when
`is_product_root()` identifies the ETHOS product repository. All other roots
receive the neutral coupling projection. This removes the file-name heuristic
instead of adding adopter-specific exceptions.

### 2. Keep direct release inspection total

`version_manifest()` accepts either a standard `[project]` identity or one
runtime-files tool table with a contained, regular, nonempty version source.
Malformed or unsupported metadata produces `release_version_manifest_invalid`
in the report. The public command therefore remains structured and does not
leak implementation tracebacks.

The same total-report rule applies to `.ethos/release.toml`: unreadable or
invalid TOML becomes `release_config_invalid:.ethos/release.toml`. Callers keep
receiving an ordinary policy report and can classify the gap without catching
a parser exception.

### 3. Preserve one compact adopter owner

The runtime-files table name is the release name. The table owns distribution
kind and version-source path; the referenced file owns the version. ETHOS does
not require an additional profile field or duplicate those facts in
`.ethos/profile.toml`.

## Risks / Trade-offs

- Multiple runtime-files tables are ambiguous and produce the structured
  invalid-manifest gap; a repository declares exactly one release owner.
- Direct release policy still reports missing product-oriented release files
  when explicitly invoked on an adopter. Generic audit paths do not invoke that
  product policy.
- Unsupported release shapes receive a structured gap rather than guessed
  metadata.

## Migration Plan

1. Add and observe the failing runtime-files regression.
2. Replace the coupling heuristic and implement the bounded identity reader.
3. Run focused tests, adopter CLI reproductions, strict OpenSpec, parity, and
   exact-HEAD proof.
4. Archive and land through the normal Work Lane lifecycle.

## Open Questions

None.
