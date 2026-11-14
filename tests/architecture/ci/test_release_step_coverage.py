"""Release steps run before a release, and tools/ci gets native tools the same way on every host."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

from ethos.adapters.repo.runtime.materialization.native_supply import NATIVE_BACKENDS

ROOT = Path(__file__).resolve().parents[3]
OWNER = ROOT / "tools/ci/toolchain/native.py"


def test_tools_ci_materializes_native_tools_only_through_the_repository_mise():
    """A hosted job keeps mise off PATH, so no session may depend on finding one there."""
    direct = sorted(
        f"{path.relative_to(ROOT)}:{number}"
        for path in (ROOT / "tools/ci").rglob("*.py")
        if path != OWNER
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if "materialize_tool(" in line
    )
    assert direct == []


def test_the_staging_command_accepts_every_registered_native_tool():
    """The staging command reads the native supply registry instead of keeping its own list."""
    environment = {"PYTHONPATH": str(ROOT / "src"), "PATH": os.environ.get("PATH", "")}
    usage = subprocess.run(
        (sys.executable, "-B", str(OWNER), "--help"),
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout
    choices = re.search(r"\{([a-z,]+)\}", usage)
    assert choices is not None
    assert set(choices[1].split(",")) == {*NATIVE_BACKENDS, "node"}


def test_each_release_platform_catalogs_its_kept_archive_in_host_conformance():
    """A conformance leg on a release leg's platform and Python runs its inventory step."""
    jobs = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))["jobs"]
    legs = jobs["release-platforms"]["strategy"]["matrix"]["include"]
    pairs = {f"{leg['host']} {leg['python']}" for leg in legs}
    steps = jobs["host-conformance"]["steps"]
    runs = [str(step.get("run", "")) for step in steps]
    catalog = next(i for i, run in enumerate(runs) if run.endswith("nox -s supply_chain"))
    assert runs.index("uv run --frozen python -m nox -s host_conformance") < catalog
    pattern = (
        r"contains\(fromJSON\('(.+)'\), format\('\{0\} \{1\}', matrix\.platform, matrix\.python\)\)"
    )
    selection = re.fullmatch(r"\$\{\{ " + pattern + r" \}\}", steps[catalog]["if"])
    assert selection is not None
    assert set(json.loads(selection[1])) == pairs
