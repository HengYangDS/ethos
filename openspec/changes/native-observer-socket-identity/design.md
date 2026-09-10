## Context

The same unprivileged Linux container observes files successfully from direct
Python, but fails when `uv` remains in the process tree. Its native observation
contains a Unix socket with an inode and no device field. The parser currently
accepts either no identity fields or both device and inode, incorrectly treating
this socket record as unavailable evidence.

## Decision

Keep the existing complete process scan and typed failure surface. Interpret
the field combinations by resource type: an explicitly identified Unix socket
may expose an inode without a filesystem device. Validate that inode, but do not
invent a device or insert a synthetic filesystem identity. Regular files and
directories still require their complete device/inode pair.

Retain rejection of malformed frames, missing process context, duplicate fields,
invalid identifiers, unknown or inaccessible resources and transport failures.
Socket support must not become a generic permission-error or partial-record
exception. The existing retirement content inventory already rejects socket
nodes inside a deletion target; that independent boundary remains unchanged.

## Verification

Extend the existing frame matrix with the observed socket record, malformed
variants and a regular-file record missing its device. Reproduce the existing
retirement tests through `uv` and Nox inside the pinned Linux image. Keep process
visibility and real permission denial intact; do not alter the CI identity
boundary again. Use exact-HEAD proof and hosted results as separate evidence.
