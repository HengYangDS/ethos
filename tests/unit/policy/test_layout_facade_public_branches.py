from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.layout.facades import dynamic_compat_facade_findings
from ethos.repository.policy.layout.facades import module_facade_findings
from ethos.repository.policy.layout.facades import package_init_facade_findings
from ethos.repository.policy.layout.facades import private_alias_findings

if TYPE_CHECKING:
    from pathlib import Path


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


def test_private_alias_audit_allows_public_aliases_and_relative_imports_without_module(
    tmp_path: Path,
) -> None:
    carrier = _write(
        tmp_path,
        "src/ethos/consumer.py",
        "import public_api as stable\n"
        "from ethos.api import Result as StableResult\n"
        "from . import sibling as _sibling\n",
    )

    assert private_alias_findings(tmp_path, {"semantic_paths": ["src"]}, files=(carrier,)) == []


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

    findings = package_init_facade_findings(tmp_path, {"semantic_paths": ["src"]}, files=(carrier,))

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

    findings = module_facade_findings(tmp_path, {"semantic_paths": ["src"]}, files=(carrier,))

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

    findings = dynamic_compat_facade_findings(
        tmp_path, {"semantic_paths": ["src"]}, files=(carrier,)
    )

    assert ([item["reasons"] for item in findings] if findings else []) == (
        [reasons] if reasons else []
    )


def test_ordinary_module_audits_skip_package_initializers(tmp_path: Path) -> None:
    carrier = _write(
        tmp_path,
        "src/ethos/sample/__init__.py",
        "def __getattr__(name):\n    return name\n",
    )
    policy = {"semantic_paths": ["src"]}

    assert module_facade_findings(tmp_path, policy, files=(carrier,)) == []
    assert dynamic_compat_facade_findings(tmp_path, policy, files=(carrier,)) == []
