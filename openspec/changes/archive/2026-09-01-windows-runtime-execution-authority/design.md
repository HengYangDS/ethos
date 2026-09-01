## Context

An ETHOS immutable runtime is copied into a staging generation, receives the
locked dependency closure and package wheel, is sealed, and is renamed to its
content digest. Python relocation is separately post-observed through
`sys.prefix` and `sys.base_prefix`.

At accepted HEAD `d18bc92f`, GitHub hosted Windows Python 3.12, 3.13, and 3.14
all pass the interpreter relocation predicate and then fail only when
`require_runtime_generation()` executes `Scripts/ethos.exe --version`. POSIX
console scripts are rewritten to locate their sibling interpreter; the Windows
branch retains the installer-generated launcher. Existing failure projection
does not preserve launcher stderr, so the launcher's internal binary encoding
is not asserted as fact. The proven defect is narrower and sufficient: the
generated launcher does not survive the runtime transition and therefore
cannot own immutable-runtime execution.

## Goals / Non-Goals

**Goals:**

- establish one runtime execution authority on every platform;
- use the validated runtime-owned Python executable plus isolated module
  execution for smoke, next actions, hooks, and internal continuations;
- delete the parallel selected-console-launcher contract;
- keep package-installed command convenience separate from immutable runtime
  identity and currentness;
- prove the same package-only path on hosted Windows 3.12, 3.13, and 3.14.

**Non-Goals:**

- reverse-engineering or patching a vendor launcher format;
- adding a Windows wrapper, PATH fallback, launcher rewrite, retry, or
  compatibility branch;
- changing external `pip`/`uv` wheel installation behavior;
- combining branch-role, proposal-retirement, tempfile, or documentation
  convergence into this atom.

## Decisions

### 1. The interpreter owns execution

The immutable runtime SHALL execute ETHOS as:

```text
<runtime-python> -B -I -m ethos.cli <arguments>
```

The runtime manifest already authenticates that interpreter and every package
file. Module execution therefore uses the same identity root without introducing
a launcher-specific path or state.

### 2. Console scripts are package projections, not runtime authority

The wheel continues to declare the public `ethos` console script for ordinary
installation. Runtime image construction removes its generated launcher bytes;
runtime selection SHALL neither store nor require them, and internal ETHOS
commands SHALL not execute them. Other locked tools retain their independently
owned relocatable console projections.

This removes responsibility rather than adding a wrapper. Deleting every
console script from the image is not required by this atom because other locked
tools may own legitimate package entrypoints; their lifecycle is independent of
the ETHOS runtime command.

The same interpreter boundary invokes the locked installer as
`python -B -I -m uv`. The `uv` package remains responsible for locating its
platform-native binary inside that same installed closure; ETHOS no longer
guesses whether it lives beside the interpreter or under `Scripts`. This does
not turn the uv binary into an ETHOS runtime identity carrier. Managed Python
selection additionally requires uv's `--system` boundary so module execution
cannot reinterpret the invoking runtime or project virtual environment as the
standalone interpreter to copy.

### 3. Post-observation reports the actual command boundary

Runtime generation smoke SHALL execute the owned Python module command. A
failure remains fail-closed and includes the exact command, return code, stdout,
and stderr in its causal error so the observation boundary is inspectable.

## Risks / Trade-offs

- [Module execution differs from the wheel console entrypoint] → Both resolve
  to `ethos.cli:main`; focused tests and package-only smoke prove the exact
  command.
- [A console script silently becomes authoritative again] → Remove it from
  `SelectedRuntime`, `runtime_command()`, finalization, and architecture-smoke
  invocation; repository-wide references must close.
- [A platform-specific Python layout regresses] → Keep native `runtime_python()`
  selection and the existing prefix checks; hosted Windows remains the final
  platform proof.

## Migration Plan

1. Add RED tests requiring selected-runtime commands and generation smoke to use
   the runtime Python module and requiring finalization without an ETHOS launcher.
2. Remove the selected launcher field and route internal invocation through one
   Python-module command constructor.
3. Update isolated-wheel smoke to exercise the same authority after relocating
   the bootstrap repository.
4. Close references, run focused tests, exact-HEAD full proof, official archive
   and reproof, candidate/accepted CAS, immutable-runtime readback, dual-Forge
   publication, and hosted Windows 3.12/3.13/3.14 verification.
