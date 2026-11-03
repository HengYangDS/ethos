# Design

## Context

See [proposal.md](proposal.md). `facade_findings` and `private_alias_findings` in
`src/ethos/repository/policy/layout/facades.py` parse each semantic Python file once and report
module-level facades and aliases; `module_layout_report` combines their findings into the gate's
gaps. On the lane head, a scan of ETHOS's product code finds five module-level functions whose one
statement passes all their parameters to a call. Only `openspec_base_command` calls a function by
name; the other four call a dictionary's `get` (`interpreter_machine`), a method of a computed value
(`actor_ref`, `binding_path`) or a lazily imported module (`_paradigm`), and each of those gives the
call its own meaning.

## Goals / Non-Goals

**Goals:**

- A new identity forward fails the module-layout gate with the file and the function.
- ETHOS's product code has none.

**Non-Goals:**

- Methods and nested functions; a method's receiver and a closure's scope are semantics of their
  own.
- Module-level assignment aliases, which stay review evidence as the design records.
- Test and tools code. The check reads the package paths that the layout policy declares,
  `src/ethos`: four test fixtures pass every parameter to a product function only to supply
  defaults, and each fixture's name states the case it builds.

## Decisions

- **The callee is a function the module names.** A forward calls a name that a `def` or an import
  binds in the module, or an attribute chain on a name that an import binds. A call on a module
  data value, such as a dictionary's `get`, or on any computed value is not a forward.
- **Every parameter, unchanged, and nothing else.** Positional parameters pass in order by
  position or by keyword, keyword-only parameters by keyword, `*args` and `**kwargs` by unpacking,
  and the call has no other argument. A default that the forward adds does not give it semantics.
- **A decorator gives semantics.** A decorated function, such as one under `lru_cache`, is never a
  forward.
- **The forward goes, the name stays.** `openspec_base_command` keeps its name, which 8 other
  product modules, 2 tools modules and 17 test modules use, and takes the body of `_base_command`;
  `run_json_batch` calls `openspec_base_command(execution_probe=False)`.

## Risks / Trade-offs

- [A test patches `openspec_base_command` and then calls `run_json_batch` without a command] → The
  batch then resolves through the patch. No test does; the OpenSpec, CLI, adoption and lane tests
  run on the change.
