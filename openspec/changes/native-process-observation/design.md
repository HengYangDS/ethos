## Invariant

The native process-command observation must preserve the full visible argument
text of each selected process. A terminal width is presentation context, not
permission to omit a runtime dependency. Native command failure remains unknown
and cannot authorize reclamation.

## Evidence And Owner

GitLab job `37785` reports one failing live-process retention test at exact
source `3472cdad230e92da41b8e3fd851e2eba4f96630d`. The failure is not a missing
package, timeout or shared Python inode defect. In the same native Linux arm64
base image, `ps -axo command=` succeeds but drops a long marker with
`COLUMNS=80` or `32`; `ps -axww -o command=` retains it. The child remains alive
through both observations. This establishes a width-sensitive observation bug;
the exact failed job's inherited width remains unobserved.

`adapters/process.py` already owns native command selection. Request full width
there so every consumer inherits the correction. Keep the runtime retirement
owner, bounded execution and unknown handling unchanged. Do not special-case
GitLab, runtime names or particular argument strings, and do not set an arbitrary
large width or rewrite the host environment.

## Verification

First strengthen the existing real-process regression with narrow width and a
long argument before the dependency. Observe RED on native Linux, repair the
native command, and repeat both the direct observer and destructive consumer.
The valid process must retain its bytes; after exact owned child exit, the same
generation must retire. Native macOS and Linux observations must agree on these
claims. Windows retains its independent native command and existing tests.

Follow focused and static checks with exact source and post-archive proof,
accepted runtime activation and exact hosted CI readback. Local macOS success
does not settle Linux CI. No failed run is retried unchanged as a substitute for
the distinguishing native counterexample.
