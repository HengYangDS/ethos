"""Python test and coverage execution for repository Nox sessions."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import tomllib
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import IO
from typing import TYPE_CHECKING
from typing import Self

from filelock import FileLock
from filelock import Timeout

from ethos.adapters.process import run_command
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.filesystem import remove_owned_path as remove_generated_path
from ethos.repository.policy.quality_reports import junit_report
from tools.ci.toolchain.environment import ProjectRuntime

if TYPE_CHECKING:
    from collections.abc import Iterator

    import nox

ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path(sys.executable)
PYTEST_CONFIG = ROOT / ".config/checks/pytest/pytest.toml"
COVERAGE_CONFIG = ROOT / ".config/checks/coverage/coverage.toml"
COVERAGE_POLICY = ROOT / ".config/checks/coverage/policy.toml"
TARGETS = ("tests/unit", "tests/architecture")


def _executable(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        message = f"required executable is unavailable: {name}"
        raise RuntimeError(message)
    return path


def _number(name: str, default: int, *, zero: bool = False) -> int:
    raw = os.getenv(name, str(default))
    valid = re.fullmatch(r"[0-9]+", raw) and (zero or int(raw) > 0)
    if not valid:
        qualifier = "non-negative" if zero else "positive"
        message = f"{name} must be a {qualifier} integer"
        raise ValueError(message)
    return int(raw)


def _parallelism(name: str, default: int) -> int | None:
    raw = os.getenv(name, str(default))
    if raw == "serial":
        return None
    if not re.fullmatch(r"[1-9][0-9]*", raw):
        message = f"{name} must be a positive integer or serial"
        raise ValueError(message)
    return int(raw)


def _head() -> str:
    return run_git(ROOT, "rev-parse", "HEAD", observation=True).stdout.strip()


def _absolute_environment_path(name: str) -> Path | None:
    value = os.getenv(name)
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else (ROOT / path).resolve()


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated environment controls for one test graph."""

    head: str
    evidence: Path
    basetemp: Path
    basetemp_owned: bool
    workers: int | None
    shards: int | None
    durations: int
    timeout: tuple[int, str] | None
    lock_wait: int
    uv_cache: Path | None
    node_package_supply: Path

    @classmethod
    def load(cls, *, node_package_supply: Path) -> Self:
        """Read the declared execution controls once."""
        evidence = ROOT / os.getenv("ETHOS_TEST_EVIDENCE_DIR", "build/evidence/quality/tests")
        configured_temp = os.getenv("ETHOS_TEST_BASETEMP")
        default_temp = Path(tempfile.gettempdir()) / f"ethos-pytest-{os.getpid()}"
        return cls(
            _head(),
            evidence,
            Path(configured_temp) if configured_temp else default_temp,
            configured_temp is None,
            _parallelism("ETHOS_TEST_WORKERS", min(8, os.cpu_count() or 1)),
            _parallelism("ETHOS_TEST_SHARDS", 1),
            _number("ETHOS_TEST_DURATIONS", 20),
            cls._pair("ETHOS_TEST_TIMEOUT_SECONDS", "ETHOS_TEST_TIMEOUT_METHOD"),
            _number("ETHOS_COVERAGE_LOCK_WAIT_SECONDS", 30, zero=True),
            _absolute_environment_path("UV_CACHE_DIR"),
            node_package_supply,
        )

    @staticmethod
    def _pair(first: str, second: str) -> tuple[int, str] | None:
        seconds, method = os.getenv(first), os.getenv(second)
        if not seconds and not method:
            return None
        if not seconds or method not in {"signal", "thread"}:
            message = f"{first} and {second}=signal|thread must be set together"
            raise ValueError(message)
        return _number(first, 1), method


class PythonTestGate:
    """Own pytest, coverage, isolation, sharding, and HEAD freshness."""

    def __init__(self, settings: Settings) -> None:
        self.s = settings
        self.coverage = settings.evidence / "coverage"
        self.pytest = settings.evidence / "pytest"
        self.allure = settings.evidence / "allure"
        self.allure_results = self.allure / "results"
        self.allure_head = self.allure / "head.txt"
        self.allure_report = self.allure / "agent"
        self.data = self.coverage / ".coverage"
        self.head_file = self.coverage / "head.txt"
        self._allure_started = False

    @classmethod
    def from_environment(cls, *, node_package_supply: Path) -> Self:
        """Create one gate from the current execution declaration."""
        return cls(Settings.load(node_package_supply=node_package_supply))

    def run_tests(self, session: nox.Session) -> None:
        """Run unit and architecture tests with branch coverage."""
        with self._coverage_lock():
            self.head_file.unlink(missing_ok=True)
            self.allure_head.unlink(missing_ok=True)
            self._allure_started = False
            try:
                self._prepare()
                self._sharded(session) if self.s.shards not in {None, 1} else self._single(session)
            finally:
                self._cleanup()
                self._stable_head()
                if self._allure_started and self._allure_result_dirs():
                    self.allure_head.write_text(self.s.head + "\n", encoding="utf-8")
            self.head_file.write_text(self.s.head + "\n", encoding="utf-8")

    def render_report(self) -> Path:
        """Rebuild Allure 3 views from this exact test attempt without executing tests."""
        remove_generated_path(self.allure_report)
        if self.allure_head.is_file() and self.allure_head.read_text().strip() != self.s.head:
            message = "allure_source_stale"
            raise RuntimeError(message)
        directories = self._allure_result_dirs()
        if not self.allure_head.is_file() or not directories:
            message = "allure_results_missing"
            raise RuntimeError(message)
        self._stable_head()
        cli = self.s.node_package_supply / "allure/cli.js"
        if not cli.is_file():
            message = "allure_cli_unavailable"
            raise RuntimeError(message)
        self.allure.mkdir(parents=True, exist_ok=True)
        command = (
            str(ProjectRuntime.discover(ROOT).node_executable()),
            str(cli),
            "agent",
            "inspect",
            "--cwd",
            str(self.allure),
            "--output",
            str(self.allure_report),
            "--report",
            "awesome",
            *(str(directory) for directory in directories),
        )
        try:
            result = run_command(ROOT, command, timeout=180)
        except (OSError, ValueError):
            remove_generated_path(self.allure_report)
            raise
        if result.returncode:
            remove_generated_path(self.allure_report)
            message = f"allure_render_failed:{result.returncode}:{result.stderr[-500:]}"
            raise RuntimeError(message)
        try:
            manifest = json.loads((self.allure_report / "manifest/human-report.json").read_text())
            run = json.loads((self.allure_report / "manifest/run.json").read_text())
            total, _ = junit_report(sorted(self.pytest.glob("junit*.xml")))
            if (
                manifest["status"] != "generated"
                or run["summary"]["stats"]["total"] != total["total"]
                or not (self.allure_report / "awesome/index.html").is_file()
            ):
                remove_generated_path(self.allure_report)
                message = "allure_report_incomplete"
                raise RuntimeError(message)
        except (OSError, ValueError, KeyError, TypeError) as error:
            remove_generated_path(self.allure_report)
            message = "allure_report_invalid"
            raise RuntimeError(message) from error
        self._stable_head()
        return self.allure_report

    def _allure_result_dirs(self) -> tuple[Path, ...]:
        if not self.allure_results.is_dir():
            return ()
        return tuple(
            sorted(
                path
                for path in self.allure_results.iterdir()
                if path.is_dir() and any(path.glob("*-result.json"))
            )
        )

    def enforce_floor(self, session: nox.Session) -> None:
        """Enforce the hard floor against current-HEAD evidence only."""
        with self._coverage_lock():
            current = (
                self.head_file.read_text(encoding="utf-8").strip()
                if self.head_file.is_file()
                else ""
            )
            if not self.data.is_file() or current != self.s.head:
                session.error(f"coverage evidence is missing or stale for {self.s.head}")
            floor = tomllib.loads(COVERAGE_POLICY.read_text(encoding="utf-8"))["current_hard_floor"]
            session.run(*self._coverage("report", f"--fail-under={floor:g}"), env=self._env())
            self._stable_head()

    @contextmanager
    def _coverage_lock(self) -> Iterator[None]:
        self.coverage.mkdir(parents=True, exist_ok=True)
        try:
            with FileLock(self.coverage / ".write.lock", timeout=self.s.lock_wait):
                yield
        except Timeout as error:
            message = f"coverage evidence lock unavailable: {self.coverage / '.write.lock'}"
            raise RuntimeError(message) from error

    def _prepare(self) -> None:
        self._cleanup()
        remove_generated_path(self.allure_report)
        for path in (self.coverage, self.pytest, self.s.basetemp):
            path.mkdir(parents=True, exist_ok=True)

    def _cleanup(self) -> None:
        for path in (
            ROOT / ".coverage",
            ROOT / "coverage.xml",
            ROOT / "junit.xml",
        ):
            remove_generated_path(path)
        if self.s.basetemp_owned:
            remove_generated_path(self.s.basetemp)

    def _stable_head(self) -> None:
        if (current := _head()) != self.s.head:
            message = f"Python test HEAD moved: {self.s.head} -> {current}"
            raise RuntimeError(message)

    def _env(self, data: Path | None = None) -> dict[str, str | None]:
        config = [
            ("core.fsmonitor", "false"),
        ]
        env: dict[str, str | None] = {
            "COVERAGE_FILE": str(data or self.data),
            "ETHOS_ACTOR": None,
            "ETHOS_NODE_PACKAGE_SUPPLY": str(self.s.node_package_supply),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_COUNT": str(len(config)),
            "GIT_TERMINAL_PROMPT": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
            "UV_CACHE_DIR": str(self.s.uv_cache) if self.s.uv_cache else None,
            "UV_PROJECT_ENVIRONMENT": str(ROOT / ".venv"),
        }
        for index, (key, value) in enumerate(config):
            env[f"GIT_CONFIG_KEY_{index}"], env[f"GIT_CONFIG_VALUE_{index}"] = key, value
        return env

    def _command(self) -> tuple[str, ...]:
        return (str(PYTHON), "-m", "pytest")

    def _args(self) -> list[str]:
        args = [
            "-c",
            str(PYTEST_CONFIG),
            "-W",
            "error",
            f"--rootdir={ROOT}",
            f"--cov-config={COVERAGE_CONFIG}",
            "--cov=src/ethos",
            f"--basetemp={self.s.basetemp}",
            f"--durations={self.s.durations}",
            "--dist=load",
            "--maxschedchunk=1",
        ]
        args[:0] = ["-n", str(self.s.workers)] if self.s.workers not in {None, 1} else []
        args += (
            [f"--timeout={self.s.timeout[0]}", f"--timeout-method={self.s.timeout[1]}"]
            if self.s.timeout
            else []
        )
        return args

    def _run(
        self,
        session: nox.Session,
        *args: str,
        data: Path | None = None,
        stdout: IO[str] | None = None,
    ) -> None:
        session.run(*self._command(), *args, env=self._env(data), stdout=stdout)

    def _coverage(self, action: str, *args: str) -> tuple[str, ...]:
        return (
            str(PYTHON),
            "-m",
            "coverage",
            action,
            f"--rcfile={COVERAGE_CONFIG}",
            f"--data-file={self.data}",
            *args,
        )

    def _single(self, session: nox.Session) -> None:
        for path in (
            *self.coverage.glob(".coverage*"),
            self.coverage / "coverage.xml",
            self.pytest,
            self.allure_results,
        ):
            remove_generated_path(path)
        self.pytest.mkdir(parents=True)
        self._allure_started = True
        self._run(
            session,
            *self._args(),
            f"--junitxml={self.pytest / 'junit.xml'}",
            f"--alluredir={self.allure_results / 'single'}",
            "--cov-report=term-missing",
            f"--cov-report=xml:{self.coverage / 'coverage.xml'}",
            "--cov-fail-under=0",
            *TARGETS,
            "-q",
        )

    def _sharded(self, session: nox.Session) -> None:
        shards = self.s.shards
        if shards is None:
            message = "sharded execution requires a positive shard count"
            raise RuntimeError(message)
        shard_dir, key = self.pytest / "shards", f"{self.s.head}:shards={shards}"
        head = shard_dir / "head.txt"
        if not head.is_file() or head.read_text(encoding="utf-8").strip() != key:
            for path in (
                *self.coverage.glob(".coverage*"),
                *self.pytest.glob("junit*.xml"),
                shard_dir,
                self.allure_results,
            ):
                remove_generated_path(path)
            shard_dir.mkdir(parents=True)
            head.write_text(key + "\n", encoding="utf-8")
        nodeids_path = self.pytest / "nodeids.txt"
        with nodeids_path.open("w", encoding="utf-8") as stream:
            self._run(
                session,
                "--collect-only",
                "-q",
                "-c",
                str(PYTEST_CONFIG),
                f"--rootdir={ROOT}",
                *TARGETS,
                stdout=stream,
            )
        nodeids = [
            line
            for line in nodeids_path.read_text(encoding="utf-8").splitlines()
            if line.startswith("tests/") and "::" in line
        ]
        if not nodeids:
            message = "pytest collect-only produced no nodeids"
            raise RuntimeError(message)
        files = []
        for index in range(1, shards + 1):
            assigned, data, marker, allure_dir = (
                nodeids[index - 1 :: shards],
                self.coverage / f".coverage.shard-{index}",
                shard_dir / f"shard-{index}.passed",
                self.allure_results / f"shard-{index}",
            )
            if not assigned:
                continue
            if (
                not data.is_file()
                or not marker.is_file()
                or marker.read_text(encoding="utf-8").strip() != key
                or not any(allure_dir.glob("*-result.json"))
            ):
                remove_generated_path(data)
                remove_generated_path(marker)
                remove_generated_path(allure_dir)
                self._allure_started = True
                self._run(
                    session,
                    *self._args(),
                    "--cov-report=",
                    "--cov-fail-under=0",
                    f"--junitxml={self.pytest / f'junit-shard-{index}.xml'}",
                    f"--alluredir={allure_dir}",
                    *assigned,
                    "-q",
                    data=data,
                )
                marker.write_text(key + "\n", encoding="utf-8")
            files.append(str(data))
        self._allure_started = True
        session.run(*self._coverage("combine", *files), env=self._env())
        session.run(
            *self._coverage("xml", "-o", str(self.coverage / "coverage.xml")), env=self._env()
        )
        session.run(*self._coverage("report", "--fail-under=0"), env=self._env())
