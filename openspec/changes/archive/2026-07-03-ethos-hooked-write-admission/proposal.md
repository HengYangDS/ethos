## Why

Terminal ETHOS already has `prewrite_guard`, but the guard remains voluntary
when write-capable hosts, shell commands, or generated outputs can mutate
tracked files without first asking the product command plane. The accepted-root
bypass is therefore not closed until prewrite is bound to hook-time mutation
admission.

This change productizes hooked write admission without inventing a long-lived
orchestration engine. A campaign remains an orchestration record over multiple
OpenSpec-backed Work Lanes; this change is one lane in that campaign and must
prove, land, closeout-apply, and retire independently before later lanes depend
on it. The campaign manifest records this as a strict serial lane topology with
`ordinal` and `depends_on` fields, not as one total Work Lane.

## What Changes

- Add an ETHOS hook admission runtime report over context, pre-tool, pre-run,
  post-write, Git fallback, and CI proof hook layers.
- Bind pre-tool and mutation-risk pre-run decisions to `prewrite_guard`.
- Fuse post-write sessions when protected roots become dirty or unexpected
  tracked paths appear.
- Expose the report through the ETHOS command plane as a maintainer/reference
  hook command.
- Update the terminal productization campaign manifest so the previous
  OpenSpec archive closeout lane is closed, this lane is active, and the lane
  dependency graph is explicit.

## Capabilities

- `ethos-adapters`: subject=hooked-write-admission; reuse=extend;
  change=modify; facet:lifecycle=runtime,validation;
  facet:surface=cli,hook; facet:authority=source,test,openspec,evidence
- `ethos-cli`: subject=hook-admission-command; reuse=extend; change=modify;
  facet:lifecycle=runtime; facet:surface=cli;
  facet:authority=source,test,docs
- `ethos-contracts`: subject=explicit-mutation-context; reuse=extend;
  change=modify; facet:lifecycle=runtime,validation;
  facet:surface=cli,schema; facet:authority=source,test,openspec
- `ethos-assistants`: subject=changed-scope-routing; reuse=extend;
  change=modify; facet:lifecycle=validation; facet:surface=skill;
  facet:authority=source,test,openspec
- `ethos-repository`: subject=terminal-openspec-productization; reuse=extend;
  change=modify; facet:lifecycle=closeout; facet:surface=docs;
  facet:authority=openspec,claim,evidence

## Out Of Scope

- This change does not install host-specific hooks into every editor, MCP
  server, shell, Git checkout, or CI provider.
- This change does not replace `ethos lane prewrite`; it binds the hook runtime
  to that existing admission primitive.
- This change does not collapse package topology, implement adopter OpenSpec
  scaffolds, or finish release distribution evolution.
