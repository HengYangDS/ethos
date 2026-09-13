## Ownership

One native tool module replaces the SCC and gitleaks installers. It reads their
existing configuration owners; version, archive digest and release identity are
never copied into Python or Forge files. Python's archive reader, FileLock and
atomic rename supply the filesystem primitives. Existing bounded download
transport remains below this owner.

## Effect

Resolve the declared platform and immutable archive, lock its repository cache,
verify cached or downloaded archive bytes, and select exactly one regular named
executable member without extracting archive paths. Verify the executable's
reported version before atomic replacement. Reuse an intact executable without
changing its inode or timestamp. Invalid supply preserves the previous bytes;
owned preparation directories are removed on every normal or failed exit.

Cache paths are explicit and resolved against the repository. Symlinked or
otherwise unsafe cache roots fail before writes. Concurrent callers share the
same bounded lock and output identity; cache growth follows declared tool/version/
platform identities, not invocation count. No apt, sudo, system installation or
ambient gitleaks/SCC shortcut remains. This does not claim safety against an
uncooperative same-UID filesystem attacker or automatic SIGKILL cleanup.
Timed-out downloads terminate their owned process group before the cache lock
and scratch are released. A real delayed-child write reproduced the escaping
transport with ordinary subprocess timeout and is now prevented.

## Consumers And Migration

The proof entrypoint prepares both tools once and receives an explicit PATH.
The secrets entrypoint prepares only the scanner through the same module.
Delete both replaced installers and migrate tests and documentation in this
Change. No compatibility scripts, alternate registry or new package manager.
The existing reference-carrier table selects native scanner and link-checker
supply declarations directly. Executable ownership must survive transport
replacement and disappear when its declaration is removed; it cannot depend on
finding an old installer script.

## Native Intent Compiler Recovery

Official OpenSpec emits RENAMED as a from/to relation without a requirements
array. The previous compiler rejected it and mislabeled rename-only intent as
spec-free. Preserve the exact relation in acceptance, validate both endpoints,
and reuse one projection discriminator. Eight regressions reproduced RED;
29 compiler cases pass after repair, and checkout-bound public prewrite passes.
An exact two-path maintainer receipt records the initial recovery because the
incumbent blocked its own repair. Hooks, installed runtimes and refs were not
modified for recovery; normal governance resumes before further source work.

## Acceptance

Run both native tools through clean supply, damaged cache, invalid checksum,
missing/nonregular archive member, wrong version, download failure and unsupported
platform cases. Verify cache reuse, no ambient substitute, concurrent preparation,
lock timeout and residue bounds. Execute the real scanner and SCC in a Linux
container as an unprivileged user with a read-only system filesystem, without
host mounts writable except one owned scratch root. Then run exact-source proof
and observe both hosted CI targets; no test count substitutes for that result.

## Proof Attempt Boundary

The interrupted validation of this Change left no result, JUnit or completion
marker, but retained temporary fixtures and partial coverage. Inspection also
showed that a same-HEAD rerun could retain an older completion marker, and that
cleanup changed hard-linked external permissions. These are failures of the
existing proof prerequisite, not reasons to introduce another executor.

The test owner invalidates its marker under the existing coverage lock before
preparation. It writes completion only after execution, cleanup and HEAD
freshness pass. A fresh single attempt removes prior fragments and sharded
outputs. Cleanup unlinks directory links, makes owned directories removable and
does not chmod external hard-linked files. Rootless native supply and test
execution remain separate owners with the same explicit effect boundary.

The quality Skill projects the causal learning loop and original-handle recovery
discipline. No new Skill, ledger, registry, daemon or persistent task entity is
introduced. SIGKILL cleanup, evidence reuse across complete input closures and
full-cycle latency retain their existing unresolved plan obligations; this
repair does not claim those properties.
