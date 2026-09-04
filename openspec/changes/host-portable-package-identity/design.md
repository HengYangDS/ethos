## Context

See [proposal.md](proposal.md). Hosted Windows package conformance built commit
`6aafe80ec1d57dc2462d3cf6f5363cc3e6ccdd4a` with source tree
`fe38ce3c319cb92a207bafd142252921bc856428`, while the commit tree is
`b1e32457fdf43d8c7e0ace1aa5bda8e4d03a6b2a`. The checkout was clean under its
host Git configuration. A local reproduction with global `core.autocrlf=true`
and no repository content policy remained clean to the host but produced 3,062
false overlay paths when `source_git_identity()` deliberately hid ambient Git
configuration. Adding and renormalizing a root Git attribute policy made the
same isolated identity observation equal the committed tree.

The same hosted run installed the wheel from `file:///D:/...`, after which
package-only hook activation returned `hook_runtime_wheel_provenance_missing`.
The resolver parses the URL and passes `/D:/...` directly to `Path`; that is not
the native Windows drive path. Python's standard-library URL-to-path conversion
already owns this platform distinction across the supported Python floor.

## Goals / Non-Goals

**Goals:**

- give Git itself one repository-owned text normalization policy for ETHOS
  source bytes;
- preserve `source_git_identity()` as the single effective-tree compiler for
  real tracked and untracked overlays;
- make a clean checkout compile to `HEAD^{tree}` independently of ambient Git
  configuration;
- resolve local wheel `file:` URLs with standard-library native path semantics;
- prove the same behavior through focused tests and native hosted package
  conformance.

**Non-Goals:**

- no provider-specific branch, hard-coded drive prefix, manual separator
  rewrite, ambient Git-config trust, or alternate build identity;
- no reclassification of actual dirty overlays as clean;
- no external-link reachability or diagnostic-projection work;
- no lane cleanup, broad repository-layout change, or dependency update.

## Decisions

### Git attributes own canonical checkout bytes

Add one root `.gitattributes` declaration that treats automatically detected
text as LF and leaves binary content binary. Git applies this repository-owned
policy during checkout, status comparison, and temporary-index staging, so the
existing source identity algorithm sees the same canonical bytes on every host.

Changing `source_git_identity()` to inherit ambient global configuration was
rejected because host policy would become identity authority. Returning
`HEAD^{tree}` whenever a separate status command says clean was rejected because
it creates a second interpretation of overlay state and can hide changes when
the two calls do not share semantics. A CI-only `core.autocrlf` override was
rejected because local Windows builds would remain divergent.

### Standard-library URL conversion owns native wheel paths

Keep URI validation in `resolve_runtime_wheel()`, but replace direct
`unquote(parsed.path)` construction with `urllib.request.url2pathname()` after
requiring a local `file:` URL. On Windows the standard library removes the URI
drive-prefix slash and applies native separators; on POSIX it preserves the
existing local-path behavior. Non-file, non-local, missing, and non-wheel
provenance continues to fail closed.

A custom Windows-path parser and a platform-name switch were rejected because
they duplicate standard-library semantics and enlarge the compatibility
surface. Falling back to package discovery, cache, or source checkout was
rejected because it would weaken provenance.

### Hosted conformance remains the native proof plane

Focused tests prove the deterministic transformations without pretending to be
Windows. The existing Linux, macOS, and Windows host-conformance matrix remains
the independent native observation that the same commit/tree survives real
checkout, build, installation, and package-only runtime activation.

## Risks / Trade-offs

- **Existing tracked text was not normalized** → add the policy and inspect the
  exact staged diff; admit no repository-wide byte rewrite unless Git reports
  one and it is reviewed explicitly.
- **A binary file is misclassified as text** → use Git's `text=auto` detection
  rather than a growing extension registry, and prove representative binary
  assets remain unchanged.
- **A `file:` URL names a non-local authority** → reject it before path
  resolution rather than silently treating a remote share as local provenance.
- **A platform-specific failure remains after both repairs** → preserve the
  hosted receipt and return to the smallest failing boundary; do not add retries
  or weaken source identity.

## Migration Plan

1. Add RED tests for a repository-owned content policy and Windows drive-letter
   wheel provenance.
2. Add the minimal root Git attribute policy and use standard-library native
   URL conversion at the existing wheel resolver.
3. Run focused source-identity, runtime-input, release-identity, and package
   acceptance tests, then strict OpenSpec and the smallest affected quality
   gates.
4. Freeze the atom, run exact-HEAD full proof, archive and re-prove, complete
   candidate/accepted CAS, install and read back a fresh immutable runtime, and
   observe native Linux, macOS, and Windows host conformance.
