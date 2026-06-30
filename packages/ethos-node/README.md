# ETHOS Node Launcher

Subject: `ethos-distribution`

This package is the npm distribution adapter for the ETHOS command plane. It is
a launcher only: command semantics remain in the Python `ethos` package and the
kernel/governance/workspace/project/agent packages.

From a source checkout it executes:

```bash
uv run --package ethos ethos
```

Outside a source checkout it attempts to run the installed Python module:

```bash
python -m ethos.cli
```
