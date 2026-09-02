## Context

See `proposal.md`. The selected immutable runtime already has one canonical
command renderer, while Work Lane start independently hard-codes a source-style
uv invocation. OpenSpec bootstrap already admits the metadata file and later
artifacts, but an exact directory request bypasses that narrow recognition and
falls into archived authority.

## Goals / Non-Goals

**Goals:**

- Derive bootstrap commands from the selected runtime authority.
- Convert an absent exact Change-root request into one precise metadata
  remediation without authorizing directory mutation.
- Preserve the existing one-artifact-at-a-time OpenSpec bootstrap.

**Non-Goals:**

- Adding compatibility runners, wrappers, or adopter-specific commands.
- Allowing recursive writes to a requested Change directory.
- Mutating AIGW, Proxy, or other adopters.

## Decisions

### Render the runtime command through the existing selector

`lane start` will call the existing runtime command renderer after the selected
runtime has been validated. This keeps `CURRENT`, manifest validation, Python
selection, and shell quoting under one owner. Reusing `uv run` was rejected
because an adopter lock need not contain the ETHOS distribution.

### Model a directory request as unresolved bootstrap intent

The scope reducer will recognize only the exact absent path
`openspec/changes/<valid-id>`. It will return a typed block whose next action
prewrites the metadata file. It will not list the directory as an authorized
path. This preserves file-granular write admission and avoids introducing a
special break-glass path.

### Resolve bootstrap before archived authority

The reducer already evaluates official bootstrap before archive fallback. The
new root-intent result stays in that branch, ensuring that historical archive
attestations cannot become the owner of a new Change.

## Risks / Trade-offs

- **Risk:** Runtime paths may contain shell-significant characters.
  **Mitigation:** Reuse the selected runtime's shell renderer.
- **Risk:** Directory intent could accidentally broaden scope.
  **Mitigation:** Return a block and one exact metadata prewrite command; never
  mark the directory covered.
- **Risk:** Existing source-product tests may encode the retired uv command.
  **Mitigation:** Replace them with selected-runtime assertions and add an
  external-adopter fixture without an ETHOS entrypoint.
