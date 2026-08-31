## Context

The Git-object adapter currently decides protection from `st_mode & 0o022` for
both Unix and Windows. That is a valid Unix representation but not a Windows
authorization fact. The Hosted Windows fixture also calls `chmod(0600)`, so the
producer and verifier share the same invalid assumption.

## Goals / Non-Goals

**Goals:**

- Keep one semantic question: can an untrusted identity modify the anchor or
  replace it through its parent directory?
- Resolve that question through POSIX ownership/mode facts on Unix and the
  Windows security descriptor/DACL on Windows.
- Fail closed when the native protection fact cannot be observed.

**Non-Goals:**

- No unconditional Windows allow, mode-bit emulation, ACL text parsing,
  third-party Windows package, compatibility carrier, or policy allowlist.
- No redesign of signature verification, publication, or independent external
  verification in this atomic Change.

## Decisions

The existing Git-object trust adapter remains the sole semantic owner. POSIX
keeps its current mode check. Windows invokes the platform-native PowerShell
security APIs already present on supported Windows hosts, obtains structured
owner and access-rule facts, and admits only a current-user-owned path whose
file and parent grant write-like rights solely to the current user, Local
System, or built-in Administrators.

ETHOS-created anchor files remove inherited Windows access rules and grant the
current user full control before atomic replacement. The Hosted fixture calls
the same product operation rather than carrying a second permission recipe.
The existing runtime-input declaration owns the standard `SYSTEMROOT` value
used to locate the platform-native executable; no new configuration surface is
introduced.

Alternatives rejected: treating all Windows paths as protected loses the
security invariant; interpreting `st_mode` repeats the current defect; adding
pywin32 creates a dependency for capability already provided by the host; and
parsing localized `icacls` text would make authority depend on presentation.

## Risks / Trade-offs

- Native observation can be unavailable or malformed. It fails closed as the
  existing unprotected gap rather than guessing.
- Windows ACLs are richer than POSIX modes. The admitted set is intentionally
  narrow and permits only the current identity plus operating-system
  administrative authorities to hold write-like rights.
- Real ACL semantics cannot be proved on a Unix host. Pure result parsing is
  covered locally, while creation and positive/negative ACL behavior are
  exercised by the Hosted Windows matrix.
