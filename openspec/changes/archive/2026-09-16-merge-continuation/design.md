## Root Cause

The fixed adopter incident has a common base without active Changes, a lane
parent containing only its publication Change, and an incoming parent containing
only the static-delivery Change. Native merge stages retain these distinctions.
The current selection and scope owners ignore them; lifecycle then compares one
status payload against every visible Change. Refresh assumes a clean rebase and
has no operation-aware continuation. Path prewrite is not merge admission.

## Design

Observe current native merge parents and conflict stages through Git. Resolve
lane-owned intent from the exact parent-to-base Change delta; a unique result
selects its existing official Change, while conflicting or multiple candidates
remain explicit. After merge, first-parent provenance preserves the selection
without a new persistent binding. Explicit selections retain their own scope.

Keep ordinary unpublished replay at its existing owner. Add a merge strategy and
continue/abort modes to `lane refresh-base`, rather than another command family.
Dry-run binds HEAD, incoming head, candidate ref, native metadata, index and
working-content digest. Apply requires the current holder and exact state;
unknown or competing native operations block. The selected runtime and policy
remain prerequisites independently of intent resolution.

New working-tree Changes participate in ambiguity; task counts cannot override
native provenance. Archive attribution follows the local completed Change even
when unchanged incoming intent remains active. Incoming Change artifacts remain
bound to their parent tree during continuation, rather than inheriting local
task completion. Ignored checkout collisions are checked from Git tree/index
observations because the installed ort implementation did not enforce the
no-overwrite-ignore option in the reproduced non-fast-forward merge.

Merge preparation uses native no-commit Git merging and leaves conflicts for the
author. Continue consumes an explicitly staged, resolved index, preserves both
parents, verifies declared commit policy through the shared creation owner, and
updates only the lane ref through the existing exact CAS executor. Cleanup is a
projection after the effect, not another acceptance or permission source.
Fresh authority is checked again before cleanup, independently of the completed
ref effect. The worktree lock coordinates cooperative effects, not arbitrary
same-UID writers or a transactional filesystem.

Abort preserves only the affected content and native merge/index metadata in
content-addressed recovery material before native rollback. It must not delete
untracked or unrelated content, claim that unknown premerge edits were restored,
or repeatedly copy a repository. A failed or interrupted effect retains exact
observations; retry first recognizes native outcome and existing evidence.

## Verification

Use real disposable Git repositories for independent two-Change parents,
conflicts, explicit selection, incompatible attribution and postmerge selection.
Exercise current authority and installed hook transports, exact-state drift,
wrong/expired holders, unresolved index, signed two-parent commits, native abort,
preserved conflict resolutions and repeated/failed effects. Source fixtures are
not shipped-runtime proof: finish with package-only and exact full proof, then
let the adopter owner perform its original-lane recovery using fresh admission.

## Execution Order

First reproduce public status and selection with the native parent structure.
Repair attribution and lifecycle projection at their sole owners. Add the native
operation boundary and stage-aware continuation with preservation regressions;
then migrate status/help/docs consumers. Freeze after focused and static checks
for exact proof, official archive, postarchive proof and installed readback.
Do not grow this Change into supply, renderer or historical identity work.
