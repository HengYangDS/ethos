# Design

## Context

`.config/checks/ty/ty.toml` selects files but no rules, so ty runs at its defaults. The
`python-types` gate runs ty with `--error-on-warning` and counts every diagnostic. Its tool is
locked exactly (`uv.lock`, ty 0.0.99). Two committee rounds (scratch `ty-strict/`) settled the
decisions below.

## Goals / Non-Goals

Goals: every rule ty offers applies to ETHOS's typed code, except a named, owned deferral, and a
ty upgrade surfaces its new rules as errors.

Non-Goals:

- `truthiness-test-of-none-union` (`ty-none-truthiness`), whose fixes are behaviour choices;
- the `unsound-*` rules (`ty-sound-any`), which `typed-reports` removes area by area;
- `tests/unit` under ty (Phase T), whose 1,170 findings come from untyped report dicts;
- type checking for governed repositories (Phase 3, `python.types`).

## Decisions

1. **Selection.** `[rules] all = "error"`, with exactly the four deferrals set to `ignore`.
   Raising rules one by one would leave a new rule silent after an upgrade.
2. **Causes over casts.**
   - A bare `dict` gets its exact parameters.
   - A guard on parsed input gets an honest `object` annotation, so the guard stays meaningful.
     A guard that the type truly guarantees is removed.
   - Correlated conditional blocks are merged rather than given placeholder bindings.
   - Overriding methods take `typing.override`.
3. **Nox sessions.** A `Session` protocol in `tools/ci` names what the sessions use: `posargs`
   read-only, and `run` with Nox's overloads. Every session module annotates with it.
   - A typed double in `tests/support` replaces the `SimpleNamespace` doubles.
   - One typed binding checks that the real session conforms, because the noxfile registers
     sessions through `getattr`.
4. **Guard.** The ty gate's test keeps one planted case per raised rule class and pins the ignored
   set by equality.

## Risks / Trade-offs

- Adding type parameters can surface new findings downstream, and the Change fixes them too: 95
  is a floor, not a budget.
- A ty upgrade may now fail the gate on a new rule. That failure is the intended signal, and the
  upgrade's own supply move resolves it.
