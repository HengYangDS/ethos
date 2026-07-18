from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _module():
    path = ROOT / "tools/ci/structural_whitespace.py"
    spec = importlib.util.spec_from_file_location("structural_whitespace", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _policy(module):
    return module.WhitespacePolicy(
        max_consecutive_blank_lines=1,
        forbid_leading_blank_lines=True,
        forbid_trailing_blank_lines=True,
        shared_extensions=frozenset({".json"}),
        shell_extensions=frozenset({".sh"}),
        shell_filenames=frozenset(),
        plain_filenames=frozenset(),
        openspec_markdown_roots=(Path("openspec/changes"), Path("openspec/specs")),
        excluded_roots=(),
    )


def test_one_blank_line_is_the_only_structural_separator(tmp_path: Path) -> None:
    module = _module()
    path = tmp_path / "valid.json"
    path.write_text('{\n  "one": 1\n}\n\n{\n  "two": 2\n}\n', encoding="utf-8")

    assert module.violations(path, _policy(module)) == ()


def test_repeated_leading_and_trailing_blank_lines_are_rejected(tmp_path: Path) -> None:
    module = _module()
    path = tmp_path / "invalid.json"
    path.write_text('\n{\n\n\n  "one": 1\n}\n\n', encoding="utf-8")

    assert module.violations(path, _policy(module)) == (
        f"{path}:1: leading blank line",
        f"{path}:7: trailing blank line",
        f"{path}:3: 2 consecutive blank lines; maximum is 1",
    )


def test_shell_heredoc_body_uses_its_embedded_language_spacing(tmp_path: Path) -> None:
    module = _module()
    path = tmp_path / "runner.sh"
    path.write_text(
        "python - <<'PY'\n"
        "def first() -> None:\n"
        "    pass\n"
        "\n"
        "\n"
        "def second() -> None:\n"
        "    pass\n"
        "PY\n",
        encoding="utf-8",
    )

    assert module.violations(path, _policy(module)) == ()


def test_shell_heredoc_body_is_not_read_as_shell_layout(tmp_path: Path) -> None:
    module = _module()
    path = tmp_path / "runner.sh"
    path.write_text("cat <<'EOF'\n\n\nvalue\nEOF\n", encoding="utf-8")

    assert module.violations(path, _policy(module)) == ()


def test_explicit_path_outside_repository_is_ignored_without_crashing(
    tmp_path: Path,
) -> None:
    module = _module()
    policy = module.load_policy(ROOT)
    outside = tmp_path / "outside.json"
    outside.write_text("{}\n", encoding="utf-8")

    assert module.selected_paths(ROOT, (outside,), policy) == ()


def test_active_openspec_markdown_uses_shared_blank_line_reader() -> None:
    module = _module()
    policy = _policy(module)

    assert module.is_governed(ROOT / "openspec/specs/quality/spec.md", policy, root=ROOT)
    assert not module.is_governed(
        ROOT / "openspec/changes/archive/example/proposal.md", policy, root=ROOT
    )


def test_policy_selects_shared_and_shell_carriers_only() -> None:
    module = _module()
    policy = module.load_policy(ROOT)

    assert module.is_governed(ROOT / "system/schemas/kernel/result.schema.json", policy, root=ROOT)
    assert module.is_governed(ROOT / "tools/ci/scripts/run-shell-lint.sh", policy, root=ROOT)
    assert module.is_governed(ROOT / ".gitattributes", policy, root=ROOT)
    assert not module.is_governed(ROOT / "README.md", policy, root=ROOT)
    assert not module.is_governed(ROOT / ".config/checks/yaml/yamllint.yaml", policy, root=ROOT)
