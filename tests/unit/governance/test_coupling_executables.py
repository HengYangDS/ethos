from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from ethos.repository.policy.coupling.execution.audit import mandatory_executable_gaps
from ethos_core.contracts.registry.declarations import CouplingDeclaration
from ethos_core.contracts.registry.declarations import load_coupling_declaration

if TYPE_CHECKING:
    from pathlib import Path

_BINDING_ID = "work_lane_lifecycle_command_contract"


def _declaration_payload(
    *mandatory_paths: str,
    declared_executables: tuple[str, ...] = ("git",),
    audit_root_bound: bool = True,
) -> dict[str, object]:
    payload = load_coupling_declaration().model_dump(mode="python", by_alias=True)
    binding = next(item for item in payload["binding"] if item["id"] == _BINDING_ID)
    binding["mandatory_paths"] = mandatory_paths
    binding["declared_executables"] = declared_executables
    binding["audit_root_bound"] = audit_root_bound
    return payload


def _declaration(
    *mandatory_paths: str,
    declared_executables: tuple[str, ...] = ("git",),
    audit_root_bound: bool = True,
) -> CouplingDeclaration:
    return CouplingDeclaration.model_validate(
        _declaration_payload(
            *mandatory_paths,
            declared_executables=declared_executables,
            audit_root_bound=audit_root_bound,
        )
    )


def _write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _gaps(root: Path, declaration: CouplingDeclaration) -> list[str]:
    return mandatory_executable_gaps(root, declaration)


def _assert_gap(gaps: list[str], kind: str, relative: str) -> None:
    assert len(gaps) == 1
    assert gaps[0].startswith(f"{kind}:{_BINDING_ID}:{relative}")


def test_declared_literal_git_is_allowed_through_aliases_and_args_keyword(
    tmp_path: Path,
) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import subprocess as process\n"
        "from subprocess import run as invoke\n"
        "process.Popen(args=('git', 'status'))\n"
        "invoke(args=['git', 'status'], shell=False, executable=None)\n",
    )

    assert _gaps(tmp_path, _declaration(relative)) == []


@pytest.mark.parametrize(
    "source",
    [
        "import os\nos.system('git status')\n",
        "from os import system\nsystem('git status')\n",
        "import os\nos.popen('git status')\n",
        "from os import popen\npopen('git status')\n",
    ],
)
def test_os_shell_execution_apis_are_rejected(tmp_path: Path, source: str) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    _assert_gap(
        _gaps(tmp_path, _declaration(relative)),
        "mandatory_executable_shell_true",
        relative,
    )


@pytest.mark.parametrize(
    ("source", "kind", "suffix"),
    [
        (
            "import subprocess\nprocess = subprocess\nprocess.run(['tar', '--version'])\n",
            "mandatory_executable_undeclared",
            ":tar",
        ),
        (
            "import asyncio\n"
            "process = asyncio\n"
            "process.create_subprocess_exec('tar', '--version')\n",
            "mandatory_executable_undeclared",
            ":tar",
        ),
        (
            "import os\nprocess = os\nprocess.popen('git status')\n",
            "mandatory_executable_shell_true",
            "",
        ),
    ],
)
def test_assigned_known_module_aliases_are_audited(
    tmp_path: Path,
    source: str,
    kind: str,
    suffix: str,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    gaps = _gaps(tmp_path, _declaration(relative))

    _assert_gap(gaps, kind, relative)
    assert gaps[0].endswith(suffix)


@pytest.mark.parametrize(
    "source",
    [
        "import subprocess\nprocess: object = subprocess\nprocess.run(['tar', '--version'])\n",
        "import subprocess\n"
        "invoke: object = getattr(subprocess, 'run')\n"
        "invoke(['tar', '--version'])\n",
        "import os\nprocess: object = os\nprocess.execv('tar', ['tar', '--version'])\n",
    ],
)
def test_annotated_known_module_and_function_aliases_are_audited(
    tmp_path: Path, source: str
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    gaps = _gaps(tmp_path, _declaration(relative))

    _assert_gap(gaps, "mandatory_executable_undeclared", relative)
    assert gaps[0].endswith(":tar")


@pytest.mark.parametrize(
    ("source", "kind", "suffix"),
    [
        (
            "import subprocess\n"
            "import os\n"
            "process = subprocess\n"
            "process = os\n"
            "process.system('git status')\n",
            "mandatory_executable_shell_true",
            "",
        ),
        (
            "import os\n"
            "import subprocess\n"
            "process = os\n"
            "process = subprocess\n"
            "process.run(['tar', '--version'])\n",
            "mandatory_executable_undeclared",
            ":tar",
        ),
        (
            "import os\ninvoke = os.execv\ninvoke = os.system\ninvoke('git')\n",
            "mandatory_executable_shell_true",
            "",
        ),
        (
            "import subprocess\n"
            "import os\n"
            "process: object = subprocess\n"
            "process: object = os\n"
            "process.system('git status')\n",
            "mandatory_executable_shell_true",
            "",
        ),
        (
            "import os\ninvoke: object = os.execv\ninvoke: object = os.system\ninvoke('git')\n",
            "mandatory_executable_shell_true",
            "",
        ),
    ],
)
def test_rebound_known_execution_aliases_fail_closed(
    tmp_path: Path,
    source: str,
    kind: str,
    suffix: str,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    gaps = _gaps(tmp_path, _declaration(relative))

    _assert_gap(gaps, kind, relative)
    assert gaps[0].endswith(suffix)


def test_execution_aliases_are_resolved_at_each_call_site(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import os\n"
        "import subprocess\n"
        "process = os\n"
        "process.system('git status')\n"
        "process = subprocess\n"
        "process.run(['tar', '--version'])\n",
    )

    gaps = _gaps(tmp_path, _declaration(relative))

    assert f"mandatory_executable_shell_true:{_BINDING_ID}:{relative}:4" in gaps
    assert f"mandatory_executable_undeclared:{_BINDING_ID}:{relative}:6:tar" in gaps


@pytest.mark.parametrize(
    ("source", "kind", "suffix"),
    [
        (
            "import os\n"
            "import subprocess\n"
            "if condition:\n"
            "    process = subprocess\n"
            "else:\n"
            "    process = os\n"
            "process.run(['tar', '--version'])\n",
            "mandatory_executable_undeclared",
            ":tar",
        ),
        (
            "import os\n"
            "import subprocess\n"
            "if condition:\n"
            "    process = subprocess\n"
            "else:\n"
            "    process = os\n"
            "process.system('git status')\n",
            "mandatory_executable_shell_true",
            "",
        ),
        (
            "import os\n"
            "import subprocess\n"
            "try:\n"
            "    process = subprocess\n"
            "except RuntimeError:\n"
            "    process = os\n"
            "process.run(['tar', '--version'])\n",
            "mandatory_executable_undeclared",
            ":tar",
        ),
    ],
)
def test_control_flow_rebound_aliases_fail_closed(
    tmp_path: Path,
    source: str,
    kind: str,
    suffix: str,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    gaps = _gaps(tmp_path, _declaration(relative))

    _assert_gap(gaps, kind, relative)
    assert gaps[0].endswith(suffix)


def test_function_call_uses_late_global_execution_binding(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "def execute():\n"
        "    process.run(['tar', '--version'])\n"
        "import subprocess as process\n"
        "execute()\n",
    )

    gaps = _gaps(tmp_path, _declaration(relative))

    _assert_gap(gaps, "mandatory_executable_undeclared", relative)
    assert gaps[0].endswith(":tar")


@pytest.mark.parametrize(
    "source",
    [
        "import subprocess\nvalue: subprocess.run(['tar', '--version'])\n",
        "import subprocess\n"
        "def execute(value: subprocess.run(['tar', '--version'])):\n"
        "    return value\n",
        "import subprocess\n"
        "def execute() -> subprocess.run(['tar', '--version']):\n"
        "    return None\n",
    ],
)
def test_evaluated_execution_annotations_are_audited(tmp_path: Path, source: str) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    gaps = _gaps(tmp_path, _declaration(relative))

    _assert_gap(gaps, "mandatory_executable_undeclared", relative)
    assert gaps[0].endswith(":tar")


@pytest.mark.parametrize(
    ("source", "kind", "suffix"),
    [
        (
            "import subprocess\ngetattr(subprocess, 'run')(['tar', '--version'])\n",
            "mandatory_executable_undeclared",
            ":tar",
        ),
        (
            "import subprocess\n"
            "process = subprocess\n"
            "invoke = getattr(process, 'run')\n"
            "invoke(['tar', '--version'])\n",
            "mandatory_executable_undeclared",
            ":tar",
        ),
        (
            "import os\ngetattr(os, 'system')('git status')\n",
            "mandatory_executable_shell_true",
            "",
        ),
        (
            "import os\ngetattr(os, 'popen')('git status')\n",
            "mandatory_executable_shell_true",
            "",
        ),
        (
            "import os\ngetattr(os, 'execvp')('tar', ['tar', '--version'])\n",
            "mandatory_executable_undeclared",
            ":tar",
        ),
        (
            "import asyncio\ngetattr(asyncio, 'create_subprocess_exec')('tar', '--version')\n",
            "mandatory_executable_undeclared",
            ":tar",
        ),
    ],
)
def test_literal_getattr_known_process_apis_are_audited(
    tmp_path: Path,
    source: str,
    kind: str,
    suffix: str,
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    gaps = _gaps(tmp_path, _declaration(relative))

    _assert_gap(gaps, kind, relative)
    assert gaps[0].endswith(suffix)


@pytest.mark.parametrize(
    "source",
    [
        "import os\ngetattr(os, 'getcwd')()\n",
        "unrelated = object()\ngetattr(unrelated, 'run')()\n",
    ],
)
def test_literal_getattr_outside_known_execution_apis_is_not_audited(
    tmp_path: Path, source: str
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert _gaps(tmp_path, _declaration(relative)) == []


@pytest.mark.parametrize(
    "source",
    [
        "import asyncio.subprocess as proc\nproc.create_subprocess_exec('tar', '--version')\n",
        "from asyncio import subprocess as proc\nproc.create_subprocess_exec('tar', '--version')\n",
        "from asyncio.subprocess import create_subprocess_exec as invoke\n"
        "invoke('tar', '--version')\n",
        "import asyncio.subprocess\n"
        "asyncio.subprocess.create_subprocess_exec('tar', '--version')\n",
        "from asyncio import subprocess\nsubprocess.create_subprocess_exec('tar', '--version')\n",
        "from asyncio.subprocess import create_subprocess_exec\n"
        "create_subprocess_exec('tar', '--version')\n",
        "import asyncio.subprocess as proc\n"
        "getattr(proc, 'create_subprocess_exec')('tar', '--version')\n",
        "from asyncio import subprocess as proc\n"
        "getattr(proc, 'create_subprocess_exec')('tar', '--version')\n",
    ],
)
def test_public_asyncio_subprocess_imports_are_audited(tmp_path: Path, source: str) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    gaps = _gaps(tmp_path, _declaration(relative))

    _assert_gap(gaps, "mandatory_executable_undeclared", relative)
    assert gaps[0].endswith(":tar")


@pytest.mark.parametrize(
    "source",
    [
        "import asyncio.subprocess as proc\nproc.create_subprocess_shell('git status')\n",
        "from asyncio import subprocess\nsubprocess.create_subprocess_shell('git status')\n",
        "from asyncio.subprocess import create_subprocess_shell\n"
        "create_subprocess_shell('git status')\n",
    ],
)
def test_public_asyncio_subprocess_shell_imports_are_audited(tmp_path: Path, source: str) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    _assert_gap(
        _gaps(tmp_path, _declaration(relative)),
        "mandatory_executable_shell_true",
        relative,
    )


@pytest.mark.parametrize(
    "source",
    [
        "import subprocess\nname = 'run'\ngetattr(subprocess, name)(['git', 'status'])\n",
        "import os\nname = 'execv'\ngetattr(os, name)('git', ['git', 'status'])\n",
    ],
)
def test_dynamic_getattr_on_known_execution_modules_fails_closed(
    tmp_path: Path, source: str
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    _assert_gap(
        _gaps(tmp_path, _declaration(relative)),
        "mandatory_executable_dynamic_argv0",
        relative,
    )


@pytest.mark.parametrize(
    "call",
    [
        "os.execv(EXECUTABLE, ['git', 'status'])",
        "os.execve(EXECUTABLE, ['git', 'status'], {})",
        "os.execvp(EXECUTABLE, ['git', 'status'])",
        "os.execvpe(EXECUTABLE, ['git', 'status'], {})",
        "os.execl(EXECUTABLE, 'git', 'status')",
        "os.execle(EXECUTABLE, 'git', 'status', {})",
        "os.execlp(EXECUTABLE, 'git', 'status')",
        "os.execlpe(EXECUTABLE, 'git', 'status', {})",
        "os.spawnv(os.P_WAIT, EXECUTABLE, ['git', 'status'])",
        "os.spawnve(os.P_WAIT, EXECUTABLE, ['git', 'status'], {})",
        "os.spawnvp(os.P_WAIT, EXECUTABLE, ['git', 'status'])",
        "os.spawnvpe(os.P_WAIT, EXECUTABLE, ['git', 'status'], {})",
        "os.spawnl(os.P_WAIT, EXECUTABLE, 'git', 'status')",
        "os.spawnle(os.P_WAIT, EXECUTABLE, 'git', 'status', {})",
        "os.spawnlp(os.P_WAIT, EXECUTABLE, 'git', 'status')",
        "os.spawnlpe(os.P_WAIT, EXECUTABLE, 'git', 'status', {})",
        "os.posix_spawn(EXECUTABLE, ['git', 'status'], {})",
        "os.posix_spawnp(EXECUTABLE, ['git', 'status'], {})",
    ],
)
def test_os_exec_and_spawn_families_validate_executable_position(tmp_path: Path, call: str) -> None:
    relative = "mandatory/effect.py"
    declaration = _declaration(relative)

    declared_call = call.replace("EXECUTABLE", "'git'")
    _write(tmp_path, relative, f"import os\n{declared_call}\n")
    assert _gaps(tmp_path, declaration) == []

    undeclared_call = call.replace("EXECUTABLE", "'tar'")
    _write(tmp_path, relative, f"import os\n{undeclared_call}\n")
    gaps = _gaps(tmp_path, declaration)
    _assert_gap(gaps, "mandatory_executable_undeclared", relative)
    assert gaps[0].endswith(":tar")

    _write(
        tmp_path,
        relative,
        f"import os\ncommand = 'git'\n{call.replace('EXECUTABLE', 'command')}\n",
    )
    _assert_gap(
        _gaps(tmp_path, declaration),
        "mandatory_executable_dynamic_argv0",
        relative,
    )


def test_assigned_subprocess_execution_alias_is_audited(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import subprocess\ninvoke = subprocess.run\ninvoke(['tar', '--version'])\n",
    )

    gaps = _gaps(tmp_path, _declaration(relative))

    _assert_gap(gaps, "mandatory_executable_undeclared", relative)
    assert gaps[0].endswith(":tar")


@pytest.mark.timeout(1)
def test_reassigned_execution_alias_terminates_and_fails_closed(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import subprocess\n"
        "invoke = subprocess.run\n"
        "invoke = subprocess.Popen\n"
        "invoke(['tar', '--version'])\n",
    )

    gaps = _gaps(tmp_path, _declaration(relative))

    _assert_gap(gaps, "mandatory_executable_undeclared", relative)
    assert gaps[0].endswith(":tar")


@pytest.mark.parametrize(
    "source",
    [
        "import subprocess\ninvoke = subprocess.run\ninvoke(['git', 'status'])\n",
        "import asyncio\nasyncio.create_subprocess_exec('git', 'status')\n",
        "import asyncio.subprocess\nasyncio.subprocess.create_subprocess_exec('git', 'status')\n",
        "from asyncio import subprocess\nsubprocess.create_subprocess_exec('git', 'status')\n",
    ],
)
def test_declared_literal_git_is_allowed_through_new_execution_boundaries(
    tmp_path: Path, source: str
) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    assert _gaps(tmp_path, _declaration(relative)) == []


def test_asyncio_exec_rejects_undeclared_executable(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import asyncio\nasyncio.create_subprocess_exec('tar', '--version')\n",
    )

    gaps = _gaps(tmp_path, _declaration(relative))

    _assert_gap(gaps, "mandatory_executable_undeclared", relative)
    assert gaps[0].endswith(":tar")


def test_asyncio_exec_rejects_dynamic_argv_zero(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import asyncio\ncommand = 'git'\nasyncio.create_subprocess_exec(command, 'status')\n",
    )

    _assert_gap(
        _gaps(tmp_path, _declaration(relative)),
        "mandatory_executable_dynamic_argv0",
        relative,
    )


@pytest.mark.parametrize(
    ("keyword", "value", "kind"),
    [
        ("shell", "True", "mandatory_executable_shell_true"),
        ("executable", "'/bin/git'", "mandatory_executable_override"),
    ],
)
def test_asyncio_exec_unsafe_keyword_options_fail_closed(
    tmp_path: Path, keyword: str, value: str, kind: str
) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        f"import asyncio\nasyncio.create_subprocess_exec('git', 'status', {keyword}={value})\n",
    )

    _assert_gap(_gaps(tmp_path, _declaration(relative)), kind, relative)


def test_asyncio_shell_execution_is_rejected(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "from asyncio import create_subprocess_shell as spawn\nspawn('git status')\n",
    )

    _assert_gap(
        _gaps(tmp_path, _declaration(relative)),
        "mandatory_executable_shell_true",
        relative,
    )


def test_undeclared_literal_executable_is_rejected(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, "import subprocess\nsubprocess.run(['tar', '--version'])\n")

    gaps = _gaps(tmp_path, _declaration(relative))

    _assert_gap(gaps, "mandatory_executable_undeclared", relative)
    assert gaps[0].endswith(":tar")


def test_dynamic_argv_zero_is_rejected(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import subprocess\ncommand = 'git'\nsubprocess.run([command, 'status'])\n",
    )

    _assert_gap(
        _gaps(tmp_path, _declaration(relative)),
        "mandatory_executable_dynamic_argv0",
        relative,
    )


def test_subprocess_keyword_dynamic_args_fail_closed(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import subprocess\ncommand = ['git', 'status']\nsubprocess.run(args=command)\n",
    )

    _assert_gap(
        _gaps(tmp_path, _declaration(relative)),
        "mandatory_executable_dynamic_argv0",
        relative,
    )


def test_command_string_is_rejected(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "from subprocess import run as invoke\ninvoke(args='git status')\n",
    )

    _assert_gap(
        _gaps(tmp_path, _declaration(relative)),
        "mandatory_executable_command_string",
        relative,
    )


def test_shell_true_is_rejected(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import subprocess\nsubprocess.run(['git', 'status'], shell=True)\n",
    )

    _assert_gap(
        _gaps(tmp_path, _declaration(relative)),
        "mandatory_executable_shell_true",
        relative,
    )


def test_non_none_executable_override_is_rejected(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import subprocess\nsubprocess.run(['git', 'status'], executable='/bin/git')\n",
    )

    _assert_gap(
        _gaps(tmp_path, _declaration(relative)),
        "mandatory_executable_override",
        relative,
    )


@pytest.mark.parametrize("function", ["Popen", "run", "call", "check_call", "check_output"])
def test_positional_executable_override_is_rejected_for_popen_apis(
    tmp_path: Path, function: str
) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        f"import subprocess\nsubprocess.{function}(['git', 'status'], -1, '/bin/sh')\n",
    )

    _assert_gap(
        _gaps(tmp_path, _declaration(relative)),
        "mandatory_executable_override",
        relative,
    )


def test_positional_shell_override_is_rejected(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import subprocess\n"
        "subprocess.Popen(\n"
        "    ['git', 'status'], -1, None, None, None, None, None, True, True\n"
        ")\n",
    )

    _assert_gap(
        _gaps(tmp_path, _declaration(relative)),
        "mandatory_executable_shell_true",
        relative,
    )


@pytest.mark.parametrize(
    "source",
    [
        "import subprocess\nsubprocess.run(['git', 'status'], **{'shell': True})\n",
        "import subprocess\noptions = {}\nsubprocess.run(['git', 'status'], **options)\n",
    ],
)
def test_expanded_process_keywords_fail_closed(tmp_path: Path, source: str) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, source)

    _assert_gap(
        _gaps(tmp_path, _declaration(relative)),
        "mandatory_executable_expanded_keywords",
        relative,
    )


def test_expanded_process_positionals_fail_closed(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import subprocess\narguments = (['git', 'status'],)\nsubprocess.run(*arguments)\n",
    )

    _assert_gap(
        _gaps(tmp_path, _declaration(relative)),
        "mandatory_executable_expanded_positionals",
        relative,
    )


@pytest.mark.parametrize("function", ["getoutput", "getstatusoutput"])
def test_implicit_shell_execution_apis_are_rejected(tmp_path: Path, function: str) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        f"from subprocess import {function} as invoke\ninvoke(['git', 'status'])\n",
    )

    _assert_gap(
        _gaps(tmp_path, _declaration(relative)),
        "mandatory_executable_shell_true",
        relative,
    )


def test_safe_positional_process_options_remain_allowed(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import subprocess\n"
        "subprocess.Popen(\n"
        "    ['git', 'status'], -1, None, None, None, None, None, True, False\n"
        ")\n",
    )

    assert _gaps(tmp_path, _declaration(relative)) == []


def test_lexical_audit_root_escape_is_rejected(tmp_path: Path) -> None:
    relative = "../outside.py"

    _assert_gap(
        _gaps(tmp_path, _declaration(relative)),
        "mandatory_executable_path_escape",
        relative,
    )


def test_symlink_audit_root_escape_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.py"
    outside.write_text("import subprocess\nsubprocess.run(['git', 'status'])\n", encoding="utf-8")
    relative = "mandatory/effect.py"
    link = tmp_path / relative
    link.parent.mkdir(parents=True)
    link.symlink_to(outside)

    _assert_gap(
        _gaps(tmp_path, _declaration(relative)),
        "mandatory_executable_path_escape",
        relative,
    )


def test_unparseable_mandatory_source_fails_closed(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, "def incomplete(:\n")

    _assert_gap(
        _gaps(tmp_path, _declaration(relative)),
        "mandatory_executable_source_unavailable",
        relative,
    )


def test_optional_modules_outside_mandatory_paths_are_not_audited(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, "import subprocess\nsubprocess.run(['git', 'status'])\n")
    _write(
        tmp_path,
        "optional/semantic_attestation.py",
        "import subprocess\nsubprocess.run(['attestor', '--verify'], shell=True)\n",
    )
    _write(
        tmp_path,
        "optional/control_replacement.py",
        "import subprocess\nsubprocess.run(['replacement', '--apply'])\n",
    )

    assert _gaps(tmp_path, _declaration(relative)) == []


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "mandatory_paths": ("mandatory/effect.py",),
            "declared_executables": ("git",),
            "audit_root_bound": False,
        },
        {
            "mandatory_paths": (),
            "declared_executables": (),
            "audit_root_bound": True,
        },
        {
            "mandatory_paths": (),
            "declared_executables": ("git",),
            "audit_root_bound": False,
        },
    ],
)
def test_binding_rejects_inconsistent_executable_audit_contract(
    overrides: dict[str, object],
) -> None:
    payload = _declaration_payload()
    binding = next(item for item in payload["binding"] if item["id"] == _BINDING_ID)
    binding.update(overrides)

    with pytest.raises(ValidationError, match="executable audit"):
        CouplingDeclaration.model_validate(payload)


def test_empty_executable_allowlist_is_an_active_deny_all_contract(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(tmp_path, relative, "import subprocess\nsubprocess.run(['git', 'status'])\n")

    gaps = _gaps(
        tmp_path,
        _declaration(relative, declared_executables=()),
    )

    _assert_gap(gaps, "mandatory_executable_undeclared", relative)
    assert gaps[0].endswith(":git")


def test_os_executable_keyword_fallbacks_are_audited(tmp_path: Path) -> None:
    relative = "mandatory/effect.py"
    _write(
        tmp_path,
        relative,
        "import os\n"
        "os.execv(file='tar', args=['tar', '--version'])\n"
        "os.execv(args=['git', 'status'])\n",
    )

    assert _gaps(tmp_path, _declaration(relative)) == [
        f"mandatory_executable_dynamic_argv0:{_BINDING_ID}:{relative}:3",
        f"mandatory_executable_undeclared:{_BINDING_ID}:{relative}:2:tar",
    ]
