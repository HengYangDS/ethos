# Tasks

- [x] **1. Reproduce lifecycle signature bypass.** Prove direct commit-object
  creation ignores effective `commit.gpgsign` and creates an unsigned lane
  materialization commit.
- [x] **2. Centralize generation-time signing.** Make the sole commit-object
  owner inherit signing configuration, verify trust, and preserve repositories
  that do not enable signing.
- [x] **3. Prove generation boundaries.** Cover signed, unsigned-policy,
  untrusted-signer, lane-start success, and pre-effect compensation behavior.
- [x] **4. Derive bounded suffix repair.** Persist an immutable receipt for one
  exact linear old/new commit and integration-ref mapping.
- [x] **5. Apply and resume suffix repair.** Consume the receipt through exact
  Git/Lease CAS and linked-worktree synchronization without a second authority.
- [x] **6. Prove the public recovery.** Cover payload drift, merge rejection,
  stale refs/Lease, interruption recovery, and the real accepted suffix shape.

After Task 6 completes, close this Change only through the governed lifecycle:
execute exact-HEAD full proof; archive that proven HEAD; execute full proof on
the archive HEAD; land and close out that proven archive HEAD; retire the lane;
then rebuild and read back the accepted package-only runtime. These are
post-task effects evidenced by exact receipts and Attestations, not tasks that
may be checked before the effects occur.
