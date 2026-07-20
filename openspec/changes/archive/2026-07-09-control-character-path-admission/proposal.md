# Control-character Path Admission

## Why

Hook and prewrite admission reason about path tokens before a write-capable host
mutates tracked files. A path token containing control characters is not a valid
repository path claim: it can hide a second path in logs, command JSON, terminal
output, or shell-oriented projections. Treating that token as a normal relative
path lets a malformed input become ambiguous evidence.

## What Changes

- Reject admission path tokens that contain ASCII control characters, including
  newline and DEL.
- Preserve the original token in command JSON so the hidden state is visible and
  auditable.
- Return a specific `prewrite_path_invalid_control_character` decision instead
  of falling through to protected-root or outside-worktree errors.
- Keep the check inside admission semantics; no new truth store, command plane,
  or provider ontology is introduced.

## Capabilities

- `repository-governance`: subject=context-bound-mutation-admission;
  reuse=extend; change=modify;
  facet:lifecycle=runtime,validation; facet:surface=hook,prewrite;
  facet:authority=source,test,openspec
- `adapters`: subject=prewrite-admission; reuse=extend;
  change=modify; facet:lifecycle=runtime,validation;
  facet:surface=hook; facet:authority=source,test,openspec

## Out Of Scope

- No Unicode normalization policy beyond ASCII control-byte rejection.
- No host-specific escaping policy.
- No new hook layer or command family.
