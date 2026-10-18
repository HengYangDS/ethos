"""Own one source-bound Node observation around a declared native command."""

from __future__ import annotations

import glob
import hashlib
import io
import json
import shlex
import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from stat import S_ISREG
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.gate_policy import observe_quality_subjects
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import run_git
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.adapters.store.state.schema import local_state_root

if TYPE_CHECKING:
    from collections.abc import Generator


def retain_attempt(root: Path, output: Path, observation: dict[str, object]) -> dict[str, object]:
    """Conserve raw measurements and adverse output in the existing immutable artifact store."""
    payload = io.BytesIO()
    with ZipFile(payload, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("observation.json", json.dumps(observation, sort_keys=True))
        for path in sorted(output.rglob("*")):
            if S_ISREG(path.lstat().st_mode):
                archive.write(path, path.relative_to(output).as_posix())
    content = payload.getvalue()
    digest = hashlib.sha256(content).hexdigest()
    path = local_state_root(root) / "artifacts" / f"{digest}.zip"
    write_content_addressed(
        path, content, collision="javascript_native_artifact_identity_collision"
    )
    return {
        "path": str(path),
        "sha256": digest,
        "size_bytes": len(content),
        "media_type": "application/zip",
    }


@dataclass(frozen=True, slots=True)
class NodeAttempt:
    """Invocation-local custody; raw file shape never authenticates a producer."""

    root: Path
    source_tree: str
    command: tuple[str, ...]
    node: str
    output: Path

    def environment(self) -> dict[str, str]:
        """Give descendant Node tests a separate native journal and raw V8 input."""
        reporter = Path(__file__).with_name("reporter.mjs")
        return {
            "NODE_V8_COVERAGE": str(self.output / "raw"),
            "NODE_OPTIONS": (
                f"--test-reporter={json.dumps(str(reporter))} "
                f"--test-reporter-destination={json.dumps(str(self.output / 'journal.jsonl'))}"
            ),
        }


@contextmanager
def command_observation(root: Path, command: tuple[str, ...], node: str) -> Generator[NodeAttempt]:
    """Bind fresh committed source and retire only this invocation's temporary input."""
    head = current_tracked_head(root)
    tree = current_tree(root, head) if head else ""
    if not tree or run_git(root, "diff", "--quiet", head, "--", check=False).returncode:
        message = "javascript_native_source_unbound"
        raise ProcessExecutionError(
            message,
            reason="native_attempt_source_binding",
            command=command,
            cwd=str(root),
        )
    with TemporaryDirectory(prefix="ethos-node-command-") as name:
        output = Path(name)
        (output / "raw").mkdir()
        yield NodeAttempt(root.resolve(), tree, command, node, output)
        if (
            current_tracked_head(root) != head
            or run_git(root, "diff", "--quiet", head, "--", check=False).returncode
        ):
            message = "javascript_native_source_changed"
            observed: dict[str, object] = {
                "language": "javascript",
                "source_tree": tree,
                "argv": command,
                "verdict": "block",
                "required_gaps": [message],
            }
            artifact = retain_attempt(root, output, observed)
            raise ProcessExecutionError(
                message,
                reason="native_attempt_source_binding",
                command=command,
                cwd=str(root),
                observation={"source_tree": tree, "artifact": artifact},
            )


def prepare_command(root: Path, command: tuple[str, ...]):
    """Select Node custody for a native executable without changing gate identity."""
    if not command or Path(command[0]).name not in {"node", "node.exe"}:
        return None
    node = shutil.which(command[0]) if not Path(command[0]).is_absolute() else command[0]
    if node is None:
        return None  # The native executor retains the original missing-command result.
    try:
        observe_quality_subjects(root)
    except ValueError as error:
        raise ProcessExecutionError(
            str(error),
            reason="native_attempt_source_binding",
            command=command,
            cwd=str(root),
        ) from error
    return command_observation(root, command, str(Path(node).resolve()))


def native_recipe(
    root: Path, tests: tuple[str, ...], node: str
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Keep a safe native Node recipe; lifecycle hooks are not silently skipped."""
    manifest = json.loads((root / "package.json").read_text(encoding="utf-8"))
    scripts = manifest.get("scripts", {})
    if not isinstance(scripts, dict) or any(key in scripts for key in ("pretest", "posttest")):
        message = "javascript_native_recipe_unsupported"
        raise ValueError(message)
    recipe = scripts.get("test")
    try:
        arguments = (
            ("--test", *map(glob.escape, tests)) if recipe is None else _node_arguments(recipe)
        )
        if recipe is not None and all(argument.startswith("-") for argument in arguments):
            arguments = (*arguments, *map(glob.escape, tests))
    except (TypeError, ValueError) as error:
        message = "javascript_native_recipe_unsupported"
        raise ValueError(message) from error
    coverage = scripts.get("test:coverage")
    coverage_arguments: tuple[str, ...] = ()
    if coverage is not None:
        try:
            tokens = _tokens(coverage)
        except (TypeError, ValueError) as error:
            message = "javascript_native_coverage_recipe_unsupported"
            raise ValueError(message) from error
        if (
            any(key in scripts for key in ("pretest:coverage", "posttest:coverage"))
            or len(tokens) < 3
            or tokens[0] != "c8"
            or tokens[-2:] != ("npm", "test")
        ):
            message = "javascript_native_coverage_recipe_unsupported"
            raise ValueError(message)
        coverage_arguments = tokens[1:-2]
    return (node, *arguments), coverage_arguments


def _tokens(recipe: object) -> tuple[str, ...]:
    if not isinstance(recipe, str):
        message = "javascript_native_recipe_unsupported"
        raise TypeError(message)
    lexer = shlex.shlex(recipe, posix=True, punctuation_chars=";&|<>")
    lexer.whitespace_split = True
    return tuple(lexer)


def _node_arguments(recipe: object) -> tuple[str, ...]:
    tokens = _tokens(recipe)
    if (
        len(tokens) < 2
        or tokens[0] != "node"
        or tokens.count("--test") > 1
        or ("--test" not in tokens and tokens[1].startswith("-"))
        or any(
            value in {"&&", "||", ";", "|", "&", ">", "<"}
            or any(character in value for character in ("$", "`"))
            or value.startswith(
                ("--test-reporter", "--experimental-test-coverage", "--test-coverage")
            )
            for value in tokens[1:]
        )
    ):
        message = "javascript_native_recipe_unsupported"
        raise ValueError(message)
    return tokens[1:]
