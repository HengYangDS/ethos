## Context

The generation owner currently concatenates process commands with every file
under `operations`, `transactions` and `ref-intent`. A historical status receipt
therefore pins an obsolete interpreter forever. The current retirement request,
progress and ref-intent contracts do not bind an executable generation: recovery
re-observes current repository authority through the selected runtime.

The cleanup plan is also computed before activation validation and reused later.
Holding the selector lock does not make that earlier process/config observation
fresh. Finally, cleanup failure reports can lose already completed removals.

## Goals

- One owner decides and executes generation retirement from current dependencies.
- History remains readable without requiring its former interpreter on disk.
- Each removal uses fresh consumer facts and exact directory identity.
- Valid activation survives unavailable cleanup observations; deletion does not.
- Reports conserve actual completed effects and remain safe to retry.

## Decisions

### Operational dependencies are distinct from recorded observations

Retain the selected runtime and hook generation, generations referenced by
effective Git configuration, and generations referenced by current native process
commands. Native checkout environment bindings also retain a runtime on which
their interpreter depends. Do not infer executable lifetime from diagnostic
text, record names, task state or a negative list of terminal statuses.

Compare resolved native path ancestry, not digest spelling. Another repository
can legitimately contain the same generation name, and a direct filesystem
alias can refer to this generation without spelling its digest. Native command
listings may omit quoting around spaces; retain possible absolute path bindings
conservatively. Traverse native directory components without treating legal
punctuation as loss of the remaining path. Stop at absent components rather than
combining every possible start/end pair in a command. Verify both path fidelity
and bounded native work. Relative or dynamic program behavior and fd/mmap
references are outside this boundary, not proved absent by parsing.

Existing operation contracts retain exact semantic inputs, not interpreter
leases. They resume through the current public command. No consumer registry or
record migration is needed to stop treating their descriptive paths as authority.
Historical files are not modified or deleted by runtime reclamation.

### Retirement is one deep module, below activation

Move candidate enumeration, dependency observation, fresh selection fencing and
deletion into `adapters/repo/runtime/retirement.py`. Its public operation returns
checked, removed, retained and deferred paths. Remove the replaced functions and
imports from hook activation; do not leave aliases or a second cleanup path.

Activation still owns config, selector, state migration and rollback. Retirement
runs only after successful activation. Missing consumer facts defer reclamation
without falsely rolling back or denying the successful activation effect.

### Revalidate at the actual destructive boundary

Under the existing selector transaction, enumerate only owned generation roots.
Before every removal, observe current dependencies again and verify the exact
directory identity selected for deletion. A newly referenced candidate becomes
retained. An unknown observation leaves pending candidates undeleted. A selector
change invalidates the operation rather than authorizing a new target.

The guarantee is fresh bounded admission among cooperating runtime actors. The
selector lock is not a global lock over processes or arbitrary external config
writes. This Change does not claim new fd/mmap observer coverage, SIGKILL
scavenging, or isolation from an uncooperative same-UID writer.

### Report effects, not an all-or-nothing fiction

If a later observation or deletion fails, preserve the exact `removed` prefix,
the currently retained resources and pending paths. A retry re-derives candidates
from current state; absence of an already removed generation is normal. Successful
repeated activation must not accumulate generation directories merely because
its previous report named their paths.

## Verification

Start with distinguishing counterexamples for historical receipt pinning and a
process/config dependency appearing after initial planning. Retain selector
drift, unsafe path, unavailable observer, failure compensation, immutable-byte
preservation and successful retry obligations. Exercise repeated install/cleanup
through the public boundary with exact before/after observations.

Use the existing complete proof and lifecycle for acceptance. The previous
publication batch's unresolved 15-second hosted-test timeout remains a separate
quality obligation; a successful retry is not its root-cause repair.

## Alternatives

Deleting old receipts or listing terminal status names only hides the model error.
A persistent consumer registry duplicates state without a current writer needing
it. Keeping all generations avoids deletion but violates bounded resource life.
The selected design removes the accidental dependency while preserving positive
live-consumer constraints and honest unknown results.

### Rejected runtime-contract memo experiment

Repeated full proof failures now identify native hook-contract cold startup as
the shared failed prerequisite, not thirteen independent business defects.
A process-local contract memo keyed by runtime digest reduced repeated queries
but did not remove first-query failure. More importantly, the lightweight test
runtime's external `.pth` source and dependency bindings are not fully contained
in that digest. The memo experiment was removed before acceptance. Preserve
current selector, manifest, configuration and executable-failure observations;
do not cache a verdict or make partial input identity stand for semantic closure.

The next repair must distinguish pure package declaration from executable
currentness at the existing native runtime/fixture owner. Reuse requires the
complete actual input relation and cold/warm equivalent decisions. Retain one
bounded source repair here only insofar as required to verify retirement; broad
test-cost and delivery-inclusive lifecycle work remain on the canonical plan.
