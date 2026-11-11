# Design

## Context

See the [proposal](proposal.md). The provider resolves `go` through `locked_tool` when the
repository declares mise tools and through `shutil.which` otherwise (`_executable`), and builds its
environment from the locked graph (`_native_environment`) plus Go's offline settings
(`_go_environment`). `run_command` starts from `os.environ`, removes the keys and prefixes it is
given, then applies `env`.

## Goals / Non-Goals

Goals: the Go gates run one consistent Go, the one ETHOS resolved.

Non-Goals: choosing a Go for a repository that declares none, removing other ambient Go settings
such as `GOFLAGS`, and changing `gofmt`, which reads no `GOROOT`.

## Decisions

1. Remove `GOROOT` through `run_command`'s `remove_env`. Removal precedes the `env` update, so a
   locked graph that sets `GOROOT` keeps its own value; only a root the locked graph did not set
   leaves.
2. The resolved executable's own root is the only consistent choice: Go derives it from the
   executable's location when `GOROOT` is unset, and ETHOS already chose the executable.
3. One helper, `_run_go`, runs every `go` subcommand with the resolved executable, the offline
   environment, `remove_env=("GOROOT",)` and the existing `MISE_` prefix removal. The four call
   sites use it.
4. The regression extends the existing real-Go behavior test: it sets `GOROOT` to an empty
   directory, which fails package listing before the change and passes after.

## Risks / Trade-offs

A person who sets `GOROOT` to choose a Go for ETHOS's gates no longer can; the repository's mise
declaration is the supported way to choose one, and it keeps working.
