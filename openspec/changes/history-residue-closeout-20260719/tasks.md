## 1. Contract And Attribution

- [x] 1.1 Validate the proposal, design, and five capability deltas with strict OpenSpec validation.
- [x] 1.2 Record a carrier-attribution table for every debt record expired on July 18, 2026, including measured source categories and replacement owners.
- [x] 1.3 Add focused failing tests for tracked projection retirement, lossless Rules V2 migration, SQLite v2 migration, conservative lease pruning, and proof retention.

## 2. Tracked Residue And Scaffold Parity

- [x] 2.1 Remove `.ethos/ENGINEERING-NOTES.md` and `.ethos/terminal-landing-plan.md`, then update the historical claim that referenced the latter.
- [x] 2.2 Remove `.ethos/assistants.toml`, its adopter template, and its required manifest entry while preserving canonical assistant projection behavior.
- [x] 2.3 Reduce `.ethos/project.toml` to active metadata plus the external `[command_plane].public = "ethos"` marker and align the adopter template.
- [x] 2.4 Remove dead release fields from product and scaffold configuration while retaining protected-ref, host, publication, and attestation policy.

## 3. Rules V2 And Source-Budget Settlement

- [x] 3.1 Make Rules V2 migration preserve the complete parsed `[quality]` tree and all active non-legacy policy while normalizing legacy rules.
- [x] 3.2 Expose dry-run and guarded apply through `ethos rules migrate`, with authorization, expected-HEAD, and tracked-write admission checks.
- [x] 3.3 Migrate the product `.ethos/rules.toml` to V2, preserve active standards/format/determinism/artifact policy, correct durable-evidence roots, and leave baseline, terminal targets, and unexpired debt unchanged.
- [x] 3.4 Retire the two bundled independent-verification reference executables, preserve their provider-neutral receipt contracts, and move indispensable assertions to canonical admission tests.
- [x] 3.5 Consolidate expired-debt carriers until live metrics are at or below `python_product=35675`, `python_tests=46865`, `python_tools=1038`, `python_other=446`, `shell=1552`, `toml=11846`, and `jinja=671`.
- [x] 3.6 Remove the ten expired debt records and their now-unused waves only after the measured category limits pass.

## 4. Versioned Local-State Maintenance

- [x] 4.1 Introduce transactional SQLite schema version 2, share the schema owner across state initializers, and remove only the retired `cache_entries` table.
- [x] 4.2 Add default read-only candidate reporting plus explicit maintenance for leases that are expired and absent from refs, worktrees, and recorded paths.
- [x] 4.3 Add proof retention that preserves current HEAD and every ref-reachable proof while pruning only ref-unreachable records in explicit maintenance mode.
- [x] 4.4 Run schema migration and maintenance against copied state, verify retained active coordination, then apply the same deterministic operation to the Work Lane local state.

## 5. Recovery Preservation And Cleanup

- [x] 5.1 Archive the complete July 9 recovery snapshot set outside `.ethos/state/` with an entry manifest and archive SHA-256.
- [x] 5.2 Verify archive extraction and every contained Git bundle, then record a HEAD-bound Chronicle preservation receipt.
- [x] 5.3 Remove the disposable `.ethos/state/residue-snapshots/` copy only after the preservation receipt verifies.
- [x] 5.4 Prune eligible obsolete proof files and orphan leases while preserving current HEAD proof and all active leases.

## 6. Evidence And Lifecycle Closeout

- [x] 6.1 Run focused rules, scaffold, SQLite, lease, proof, local-state, release, assistant, and source-budget tests and gates.
- [ ] 6.2 Run the complete test suite with the configured 100% coverage floor and all quality owner scripts.
- [ ] 6.3 Commit parity-relevant changes, regenerate stale parity evidence in the admitted Work Lane, and commit the result.
- [ ] 6.4 Produce Chronicle and claim evidence that binds the cleanup predicates, preservation digest, source-budget metrics, and final Git HEAD.
- [ ] 6.5 Record the committed pre-archive status, plan, validation, lifecycle handoff, and remote deferred/unclaimed boundary.

The official archive, final HEAD-bound executed proof, candidate land,
accepted-root closeout, local publish readiness, owned-lane retirement, and any
future r7 replay are post-archive lifecycle transitions. They are governed
outside this carrier checklist and are not asserted complete before they occur.
