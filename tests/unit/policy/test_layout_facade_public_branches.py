"""Distinguish owned behavior from private aliases and empty compatibility facades."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.layout.facades import facade_findings
from ethos.repository.policy.layout.facades import identity_forward_findings
from ethos.repository.policy.layout.facades import private_alias_findings

if TYPE_CHECKING:
    from pathlib import Path

_SRC = {"semantic_paths": ["src"]}


def _write(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def test_private_alias_audit_reports_direct_and_from_import_compatibility_aliases(
    tmp_path: Path,
) -> None:
    carrier = _write(
        tmp_path,
        "src/ethos/consumer.py",
        "import public_api as _legacy\nfrom ethos.api import Result as _Result\n",
    )

    findings = private_alias_findings(tmp_path, {"semantic_paths": ["src"]}, files=(carrier,))

    assert [(item["source"], item["alias"]) for item in findings] == [
        ("public_api", "_legacy"),
        ("ethos.api.Result", "_Result"),
    ]


def test_private_alias_audit_allows_namespace_aliases_and_relative_imports_without_module(
    tmp_path: Path,
) -> None:
    carrier = _write(
        tmp_path,
        "src/ethos/consumer.py",
        "import public_api as stable\nfrom . import sibling as _sibling\n",
    )

    assert private_alias_findings(tmp_path, {"semantic_paths": ["src"]}, files=(carrier,)) == []


@pytest.mark.parametrize(
    ("source", "renamed"),
    [
        ("from ethos.api import Result as Stable\n", True),
        ("from ethos.api import Result as Stable\ndef use(Result):\n    return Stable\n", True),
        ("from yaml import loader as yaml_loader\n", True),
        ("from ethos.api import Result as Stable\nclass Result(Stable):\n    pass\n", False),
        ("from ethos.api import Result as Stable\nif FLAG:\n    from other import Result\n", False),
        ("from ethos import api as owner\nfrom ethos.api import Result as Result\n", False),
    ],
)
def test_alias_audit_reports_renames_that_no_collision_or_module_namespace_needs(
    tmp_path: Path, source: str, *, renamed: bool
) -> None:
    """A from-import keeps the canonical name unless the module already binds that name."""
    _write(tmp_path, "src/ethos/api.py", "class Result:\n    pass\n")
    _write(tmp_path, "src/ethos/consumer.py", source)

    findings = private_alias_findings(tmp_path, {"semantic_paths": ["src"]})

    assert [item["gap"].split(":")[0] for item in findings] == (
        ["module_layout_import_rename"] if renamed else []
    )


@pytest.mark.parametrize(
    ("source", "reasons"),
    [
        ('"""package"""\nfrom .api import Result\n', ["import"]),
        ('"""package"""\nfrom .api import Result\nfrom .other import Value\n', ["import"]),
        ('"""package"""\nVALUE = 1\n', ["runtime_code"]),
        ("from .api import Result\nVALUE = 1\n", ["import", "runtime_code"]),
        ('"""package"""\npass\n', []),
    ],
)
def test_package_init_audit_classifies_public_runtime_facades(
    tmp_path: Path, source: str, reasons: list[str]
) -> None:
    carrier = _write(tmp_path, "src/ethos/sample/__init__.py", source)

    findings = facade_findings(tmp_path, _SRC, files=(carrier,))["package_init_facade_findings"]

    assert ([item["reasons"] for item in findings] if findings else []) == (
        [reasons] if reasons else []
    )


@pytest.mark.parametrize(
    ("source", "expected_count"),
    [
        (
            (
                "from __future__ import annotations\n"
                "from typing import TYPE_CHECKING\n"
                "if TYPE_CHECKING:\n    from ethos.api import Result\n"
            ),
            1,
        ),
        ("from ethos.api import Result\ndef use():\n    return Result\n", 0),
        ("import ethos.api\n", 1),
        ("if ENABLED:\n    import ethos.api\n", 0),
        ("pass\n", 0),
        ("__all__ = ['Result']\n", 0),
    ],
)
def test_module_facade_audit_distinguishes_import_shells_from_owned_runtime(
    tmp_path: Path, source: str, expected_count: int
) -> None:
    carrier = _write(tmp_path, "src/ethos/sample.py", source)

    findings = facade_findings(tmp_path, _SRC, files=(carrier,))["module_facade_findings"]

    assert len(findings) == expected_count


@pytest.mark.parametrize(
    ("source", "reasons"),
    [
        ("def __getattr__(name):\n    return name\n", ["dynamic_export"]),
        (
            "async def __getattr__(name):\n    from ethos import api\n    return api\n",
            ["dynamic_export", "lazy_import"],
        ),
        ("def ordinary(name):\n    return name\nVALUE = 1\n", []),
    ],
)
def test_dynamic_compatibility_audit_exposes_lazy_module_exports(
    tmp_path: Path, source: str, reasons: list[str]
) -> None:
    carrier = _write(tmp_path, "src/ethos/sample.py", source)

    findings = facade_findings(tmp_path, _SRC, files=(carrier,))["dynamic_compat_facade_findings"]

    assert ([item["reasons"] for item in findings] if findings else []) == (
        [reasons] if reasons else []
    )


def test_ordinary_module_audits_skip_package_initializers(tmp_path: Path) -> None:
    carrier = _write(
        tmp_path, "src/ethos/sample/__init__.py", "def __getattr__(name):\n    return name\n"
    )
    policy = {"semantic_paths": ["src"]}

    findings = facade_findings(tmp_path, policy, files=(carrier,))
    assert findings["module_facade_findings"] == findings["dynamic_compat_facade_findings"] == []


_IMPORTED = "from ethos.api import load\n"


@pytest.mark.parametrize(
    ("source", "forwards"),
    [
        (
            _IMPORTED + "def read(path, *, strict=True):\n    return load(path, strict=strict)\n",
            True,
        ),
        (
            (
                "def _base(*, probe):\n    return probe\n\n\n"
                'def base(*, probe=True):\n    """Doc."""\n    return _base(probe=probe)\n'
            ),
            True,
        ),
        (
            "import ethos.api\ndef read(*paths, **kw):\n    return ethos.api.load(*paths, **kw)\n",
            True,
        ),
        (_IMPORTED + "async def read(path):\n    return await load(path=path)\n", True),
        (_IMPORTED + "def read(path):\n    return load(path, strict=True)\n", False),
        (_IMPORTED + "def read(path, strict):\n    return load(strict, path)\n", False),
        (_IMPORTED + "def read(path):\n    return load(path.name)\n", False),
        ("_TABLE = {}\ndef read(key, default):\n    return _TABLE.get(key, default)\n", False),
        (_IMPORTED + "def read(path):\n    return load().read(path)\n", False),
        (
            "from functools import cache\n"
            + _IMPORTED
            + "@cache\ndef read(p):\n    return load(p)\n",
            False,
        ),
        (
            _IMPORTED + "class Reader:\n    def read(self, path):\n        return load(path)\n",
            False,
        ),
    ],
)
def test_identity_forward_audit_reports_functions_that_only_forward_their_parameters(
    tmp_path: Path, source: str, *, forwards: bool
) -> None:
    carrier = _write(tmp_path, "src/ethos/sample.py", source)

    findings = identity_forward_findings(tmp_path, _SRC, files=(carrier,))

    name = "base" if "def base" in source else "read"
    assert [item["gap"] for item in findings] == (
        [f"module_layout_identity_forward:src/ethos/sample.py:{name}"] if forwards else []
    )
