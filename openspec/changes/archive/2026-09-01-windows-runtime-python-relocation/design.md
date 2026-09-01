## Context

See `proposal.md` for motivation. ETHOS copies a uv-managed standalone CPython
into a content-addressed runtime generation, installs the locked dependency
closure and wheel into that copy, seals it, and then executes the copy to prove
that `sys.prefix` and `sys.base_prefix` equal the generated interpreter root.

The Windows copy already has the correct native filesystem layout. The remaining
failure is in observation: `sys.prefix` and `sys.base_prefix` use native Windows
separators while `Path.resolve().as_posix()` renders the expected root with
forward slashes. Raw string equality therefore rejects one filesystem identity.

## Goals / Non-Goals

**Goals:**

- compare prefix observations by native filesystem identity;
- preserve exact fail-closed detection of a genuinely external prefix;
- prove relocation through the existing runtime-generation post-observation and
  the isolated-wheel Windows matrix.

**Non-Goals:**

- inventing a wrapper, setting `PYTHONHOME`, probing alternate executable paths,
  or accepting a source prefix;
- changing package selection, dependency supply, runtime identity, or POSIX
  image construction;
- addressing GitLab identity drop or any general hosted process-spawn issue.

## Decisions

### 1. Compare paths as paths instead of serialized text

Runtime post-observation SHALL canonicalize only for platform-native path
comparison. Windows comparison accepts equivalent separator and case forms;
POSIX comparison retains resolved path identity. The manifest continues to
store canonical portable paths independently of this filesystem predicate.

Rejected alternatives are a wrapper, `PYTHONHOME`, PATH manipulation, copying
speculative metadata, or weakening the prefix check. Each would either introduce
a second runtime authority or repair a representation mismatch at the wrong
boundary.

### 2. Keep executable post-observation authoritative

File presence is only construction evidence. `require_runtime_generation()`
continues to execute the generated interpreter and require both observed
prefixes to equal the immutable runtime root. The focused unit regression proves
that the prefix-defining artifact is copied; hosted Windows proves that CPython
actually consumes it.

### 3. Change only the Windows image branch

POSIX standalone materialization is already executable and remains unchanged.
The repair belongs to runtime-generation post-observation, which owns the
predicate being evaluated, rather than Python copying, selection, or hook
binding.

## Risks / Trade-offs

- [Normalization could hide a different path] → Use the platform path model,
  not lexical replacement or suffix comparison; genuinely different roots stay
  unequal.
- [The unit test cannot execute a Windows binary on macOS] → Test the precise
  path predicate locally and retain hosted Windows execution as final
  acceptance.
- [The source distribution changes shape] → Reject materialization rather than
  synthesizing a fallback or accepting an external prefix.

## Migration Plan

1. Record the exact hosted failure and add a focused RED for equivalent Windows
   path spellings.
2. Replace raw string equality with one native path-identity predicate.
3. Run focused runtime tests and local POSIX isolated-wheel smoke.
4. Complete exact-HEAD proof, archive/reproof, candidate and accepted CAS,
   immutable runtime readback, dual-Forge publication, and Windows 3.12/3.13/3.14
   hosted verification.
