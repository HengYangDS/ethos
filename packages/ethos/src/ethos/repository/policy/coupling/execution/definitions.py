"""Known execution API contracts used by the coupling audit."""

from __future__ import annotations

SUBPROCESS_EXECUTION_FUNCTIONS = frozenset(
    {
        "Popen",
        "call",
        "check_call",
        "check_output",
        "getoutput",
        "getstatusoutput",
        "run",
    }
)
OS_EXECUTABLE_POSITIONS = {
    "execl": 0,
    "execle": 0,
    "execlp": 0,
    "execlpe": 0,
    "execv": 0,
    "execve": 0,
    "execvp": 0,
    "execvpe": 0,
    "posix_spawn": 0,
    "posix_spawnp": 0,
    "spawnl": 1,
    "spawnle": 1,
    "spawnlp": 1,
    "spawnlpe": 1,
    "spawnv": 1,
    "spawnve": 1,
    "spawnvp": 1,
    "spawnvpe": 1,
}
OS_EXECUTION_FUNCTIONS = frozenset({"popen", "system"}.union(OS_EXECUTABLE_POSITIONS))
EXECUTION_FUNCTIONS_BY_MODULE = {
    "asyncio": frozenset({"create_subprocess_exec", "create_subprocess_shell"}),
    "os": OS_EXECUTION_FUNCTIONS,
    "subprocess": SUBPROCESS_EXECUTION_FUNCTIONS,
}
ASYNCIO_EXEC_FUNCTION = "asyncio.create_subprocess_exec"
DYNAMIC_EXECUTION_FUNCTION_SUFFIX = ".<dynamic>"
IMPLICIT_SHELL_FUNCTIONS = frozenset(
    {
        "asyncio.create_subprocess_shell",
        "os.popen",
        "os.system",
        "subprocess.getoutput",
        "subprocess.getstatusoutput",
    }
)
POPEN_EXECUTABLE_POSITION = 2
POPEN_SHELL_POSITION = 8
