"""Python test and coverage execution for repository Nox sessions."""

from __future__ import annotations

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

from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from collections.abc import Iterator

    import nox

ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path(sys.executable)
PYTEST_CONFIG = ROOT / ".config/checks/pytest/pytest.ini"
COVERAGE_CONFIG = ROOT / ".config/checks/coverage/coverage.ini"
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


def remove_generated_path(path: Path) -> None:
    """Remove one generated path without hiding cleanup failures."""
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def _chown(path: Path, uid: int, gid: int) -> None:
    if not path.exists():
        return
    for child in (path, *path.rglob("*")):
        shutil.chown(child, user=uid, group=gid)


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated environment controls for one test graph."""

    head: str
    evidence: Path
    basetemp: Path
    workers: int | None
    shards: int | None
    durations: int
    timeout: tuple[int, str] | None
    lock_wait: int
    identity: tuple[int, int] | None

    @classmethod
    def load(cls) -> Self:
        """Read the declared execution controls once."""
        evidence = ROOT / os.getenv("ETHOS_TEST_EVIDENCE_DIR", "build/evidence/quality/tests")
        default_temp = Path(tempfile.gettempdir()) / f"ethos-pytest-{os.getpid()}"
        return cls(
            _head(),
            evidence,
            Path(os.getenv("ETHOS_TEST_BASETEMP", str(default_temp))),
            _parallelism("ETHOS_TEST_WORKERS", 8),
            _parallelism("ETHOS_TEST_SHARDS", 1),
            _number("ETHOS_TEST_DURATIONS", 20),
            cls._pair("ETHOS_TEST_TIMEOUT_SECONDS", "ETHOS_TEST_TIMEOUT_METHOD"),
            _number("ETHOS_COVERAGE_LOCK_WAIT_SECONDS", 30, zero=True),
            cls._identity(),
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

    @staticmethod
    def _identity() -> tuple[int, int] | None:
        uid, gid = os.getenv("ETHOS_TEST_RUN_AS_UID"), os.getenv("ETHOS_TEST_RUN_AS_GID")
        if not uid and not gid:
            return None
        if not uid or not gid or not uid.isdecimal() or not gid.isdecimal() or "0" in {uid, gid}:
            message = "ETHOS_TEST_RUN_AS_UID/GID must be positive integers set together"
            raise ValueError(message)
        if os.getuid() != 0 or shutil.which("setpriv") is None:
            message = "test identity drop requires a root launcher and setpriv"
            raise ValueError(message)
        return int(uid), int(gid)


class PythonTestGate:
    """Own pytest, coverage, isolation, sharding, and HEAD freshness."""

    def __init__(self, settings: Settings) -> None:
        self.s = settings
        self.coverage = settings.evidence / "coverage"
        self.pytest = settings.evidence / "pytest"
        self.data = self.coverage / ".coverage"
        self.head_file = self.coverage / "head.txt"
        self.identity_home = Path(tempfile.gettempdir()) / f"ethos-test-{os.getpid()}"

    @classmethod
    def from_environment(cls) -> Self:
        """Create one gate from the current execution declaration."""
        return cls(Settings.load())

    def run_tests(self, session: nox.Session) -> None:
        """Run unit and architecture tests with branch coverage."""
        with self._coverage_lock():
            self._prepare()
            try:
                self._sharded(session) if self.s.shards not in {None, 1} else self._single(session)
                self.head_file.write_text(self.s.head + "\n", encoding="utf-8")
            finally:
                self._cleanup()
                self._stable_head()

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
        for path in (self.coverage, self.pytest, self.s.basetemp):
            path.mkdir(parents=True, exist_ok=True)
        if self.s.identity:
            self.identity_home.mkdir(parents=True, exist_ok=True)
            for path in (ROOT / "build", self.s.basetemp, self.identity_home):
                _chown(path, *self.s.identity)

    def _cleanup(self) -> None:
        for path in (
            ROOT / ".coverage",
            ROOT / "coverage.xml",
            ROOT / "junit.xml",
        ):
            remove_generated_path(path)
        for path in (ROOT / "src").rglob("__pycache__"):
            remove_generated_path(path)
        if self.s.identity:
            _chown(ROOT / "build", 0, 0)
            _chown(self.s.basetemp, 0, 0)
            remove_generated_path(self.identity_home)

    def _stable_head(self) -> None:
        if (current := _head()) != self.s.head:
            message = f"Python test HEAD moved: {self.s.head} -> {current}"
            raise RuntimeError(message)

    def _env(self, data: Path | None = None) -> dict[str, str | None]:
        config = [
            ("core.fsmonitor", "false"),
            ("credential.helper", ""),
            ("init.templateDir", ""),
        ]
        config += (
            [("safe.directory", str(ROOT)), ("safe.directory", str(ROOT / ".git"))]
            if self.s.identity
            else []
        )
        env: dict[str, str | None] = {
            "COVERAGE_FILE": str(data or self.data),
            "ETHOS_ACTOR": None,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_COUNT": str(len(config)),
            "PYTHONDONTWRITEBYTECODE": "1",
            "UV_PROJECT_ENVIRONMENT": str(ROOT / ".venv"),
        }
        for index, (key, value) in enumerate(config):
            env[f"GIT_CONFIG_KEY_{index}"], env[f"GIT_CONFIG_VALUE_{index}"] = key, value
        if self.s.identity:
            env |= {
                "HOME": str(self.identity_home),
                "XDG_CACHE_HOME": str(self.identity_home / ".cache"),
            }
        return env

    def _command(self) -> tuple[str, ...]:
        prefix = (
            (
                "setpriv",
                f"--reuid={self.s.identity[0]}",
                f"--regid={self.s.identity[1]}",
                "--clear-groups",
            )
            if self.s.identity
            else ()
        )
        return (*prefix, str(PYTHON), "-m", "pytest")

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
            "--dist=loadscope",
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
        return (str(PYTHON), "-m", "coverage", action, f"--data-file={self.data}", *args)

    def _single(self, session: nox.Session) -> None:
        for path in (self.data, self.coverage / "coverage.xml", self.pytest / "junit.xml"):
            remove_generated_path(path)
        self._run(
            session,
            *self._args(),
            f"--junitxml={self.pytest / 'junit.xml'}",
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
            assigned, data, marker = (
                nodeids[index - 1 :: shards],
                self.coverage / f".coverage.shard-{index}",
                shard_dir / f"shard-{index}.passed",
            )
            if not assigned:
                continue
            if (
                not data.is_file()
                or not marker.is_file()
                or marker.read_text(encoding="utf-8").strip() != key
            ):
                remove_generated_path(data)
                remove_generated_path(marker)
                self._run(
                    session,
                    *self._args(),
                    "--cov-report=",
                    "--cov-fail-under=0",
                    f"--junitxml={self.pytest / f'junit-shard-{index}.xml'}",
                    *assigned,
                    "-q",
                    data=data,
                )
                marker.write_text(key + "\n", encoding="utf-8")
            files.append(str(data))
        session.run(*self._coverage("combine", *files), env=self._env())
        session.run(
            *self._coverage("xml", "-o", str(self.coverage / "coverage.xml")), env=self._env()
        )
        session.run(*self._coverage("report", "--fail-under=0"), env=self._env())
