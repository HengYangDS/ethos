## Context

The diagnostic proposal run failed identically on Python 3.12, 3.13, and 3.14.
Windows PowerShell reported that `Get-Acl` was found in
`Microsoft.PowerShell.Security` but that the module could not be loaded. The
GitHub job itself runs under PowerShell 7; ETHOS then launches
`powershell.exe` while inheriting the parent environment.

## Goals / Non-Goals

**Goals:**

- Let Windows PowerShell rebuild its own native module search path.
- Preserve every unrelated inherited environment variable and the explicit
  trust-anchor path.
- Keep the existing ACL producer and observer as the sole permission model.

**Non-Goals:**

- No retry, shell fallback, hard-coded module installation, pywin32 dependency,
  POSIX-mode emulation, or unconditional Windows acceptance.
- No unrelated lifecycle, publication, tempfile, or adopter repair.

## Decisions

The shared subprocess runner gains one narrow ability to omit explicitly named
inherited variables before applying command-specific additions. The Windows
trust-anchor boundary uses it only for `PSModulePath`. This follows the native
PowerShell process contract: a Windows PowerShell child must construct its own
default module path rather than consume a value inherited from another
PowerShell edition.

The ACL script itself remains unchanged. A focused regression first proves that
the adapter requests removal of `PSModulePath`; a runner regression proves the
variable is absent in the child while ordinary environment values and explicit
overrides remain available.

## Risks / Trade-offs

- **Shared runner surface:** the omission option is explicit and defaults to an
  empty tuple, so existing callers retain byte-for-byte environment behavior.
- **Diagnostic loss:** bounded exit code and stderr preservation remains in the
  adapter, so any subsequent native failure stays observable.

## Migration Plan

Add the failing environment-boundary regressions, implement the smallest runner
and caller change, pass focused and exact-HEAD proof, archive, promote, activate
the immutable runtime, publish `dev` then `main` to both peers, verify the Hosted
Windows matrix, remove the proposal projection, and retire the Work Lane.
