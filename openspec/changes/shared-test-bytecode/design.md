## Context

See [proposal.md](proposal.md). The gate disables bytecode writes because its unprivileged hosted
identity may write only under `build/` and the temporary directory. Python still reads compiled
modules when writes are disabled, and `sys.pycache_prefix` moves every bytecode lookup, including
the standard library's, into one directory.

## Goals / Non-Goals

**Goals:**

- Each test process loads compiled modules instead of compiling them again.
- No test process runs bytecode that differs from its current source.

**Non-Goals:**

- Caching pytest's rewritten test modules.
- Changing test timeouts, worker counts or test order.

## Decisions

- Compile with `compileall --invalidation-mode checked-hash`, so Python checks each module's
  source hash before it uses the bytecode. Timestamp bytecode, the default, trusts modification
  time and size: a dependency upgrade whose wheel keeps the old timestamps, or an edit with the same
  second and size, would run the old code.
- Keep `PYTHONDONTWRITEBYTECODE=1` and compile only the declared sources. If test processes wrote
  their own bytecode, modules that tests generate and rewrite would be cached by timestamp too.
- Write the cache under `build/runtime/tool-cache/python-bytecode` through `pycache_prefix`, not
  next to the sources. The unprivileged identity cannot write the source tree or the environment,
  and the artifact topology already admits tool caches there. `uv sync --compile-bytecode` would
  cover only installed packages, not `src`, and would write into the environment.
- Enable the prefix only after `compileall` exits 0. A prefix also hides the interpreter's own
  standard-library bytecode, so a partial cache would be slower than none. On failure the gate keeps
  today's behavior and logs one `ethos_test_bytecode` line.
- Keep compilation in `tools/ci/python_test_bytecode.py`; the gate only hands the prefix to test
  processes. Compiling is a separate responsibility from running tests, and the gate is close to
  the shared 512-line ceiling.
- Compile in the Nox `tests` session before `run_tests`. Gate tests that drive `run_tests` with a
  substitute session stay unaffected.

## Risks / Trade-offs

- [`compileall` cannot skip hash-checked bytecode, so each run recompiles every declared source] →
  It runs in parallel; on the 18-core host it takes about 3 seconds.
- [A dependency ships a file that does not compile] → `compileall` fails, the gate runs without the
  prefix as before, and the log names the failure.
- [`compileall -j 0` needs process semaphores that some sandboxes deny] → Compilation fails there,
  and the gate keeps today's behavior.
