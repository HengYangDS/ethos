"""The product-hook step passes only when pre-commit admits the edit and names the refusal."""

import os
import subprocess
from contextlib import nullcontext
from functools import partial

import pytest

from tools.ci.delivery.acceptance.product_hook import prove_product_hook

# A stand-in runtime: `hook install` writes one hook into the root named by `--root` and selects
# its directory; `lane start` adds the Work Lane beside that root.
_RUNTIME = """#!/bin/sh
kind=$7; while [ "$1" != --root ]; do shift; done; h="$2/.git/s"
if [ "$kind" = hook ]; then mkdir "$h" && printf '#!/bin/sh\\n%s\\n' 'HOOK' >"$h/pre-commit"
  chmod +x "$h/pre-commit" && git -C "$2" config core.hooksPath "$h"
else git -C "$2" worktree add -q -b work/lane "$2/../lane" candidate/dev; fi
echo '{"schema_version": 1, "verdict": "pass", "data": {"path": "'"$2/../lane"'"}}'
"""
_REFUSAL = "pre_commit_text_layout:.gitignore:1"
_LAYOUT = f"git show :.gitignore | head -n 1 | grep -q . || {{ echo {_REFUSAL} >&2; exit 1; }}"
_DEFECT = "format_selection_increment_invalid"


def _run(*command, cwd, env=None):
    done = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, check=False)
    if done.returncode:
        raise RuntimeError(done.stderr)
    return done.stdout


_STEP = partial(prove_product_hook, environment=os.environ, run=_run)


@pytest.mark.skipif(os.name == "nt", reason="POSIX stand-in runtime")
@pytest.mark.parametrize(
    ("hook", "outcome"),
    # The layout rule passes; a hook that refuses every commit, as the incident's did, fails the
    # admitted case; one that admits every commit fails the refused case.
    [
        (_LAYOUT, nullcontext()),
        (f"echo {_DEFECT} >&2; exit 1", pytest.raises(RuntimeError, match=_DEFECT)),
        ("exit 0", pytest.raises(RuntimeError, match="package_product_hook_refusal_missing")),
    ],
    ids=["layout-rule", "refuses-every-commit", "admits-every-commit"],
)
def test_step_requires_admission_and_named_refusal(tmp_path, hook, outcome):
    source, python = tmp_path / "source", tmp_path / "runtime/python/bin/python"
    _run("git", "init", "--quiet", "--initial-branch=dev", str(source), cwd=tmp_path)
    (source / ".gitignore").write_text("/build/\n", encoding="utf-8")
    _run("git", "add", ".gitignore", cwd=source)
    _run("git", "commit", "--quiet", "--message=init", cwd=source)
    python.parent.mkdir(parents=True)
    python.write_text(_RUNTIME.replace("HOOK", hook), encoding="utf-8")
    python.chmod(0o755)
    head = _run("git", "rev-parse", "HEAD", cwd=source).strip()
    with outcome:
        observed = _STEP(python.parents[2], source, head=head, work=tmp_path / "work")
        assert observed == {"state": "passed", "head": head, "admitted": True, "refused": _REFUSAL}
