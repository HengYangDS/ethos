"""The shell and command-wrapper vocabulary that command references are read with."""

from __future__ import annotations

# The options that take a value for each prefix command that runs the command after it.
PREFIX_OPTIONS = {
    "nice": frozenset({"-n", "--adjustment"}),
    "nohup": frozenset(),
    "sudo": frozenset({"-u", "--user", "-g", "--group", "-p", "--prompt", "-h", "--host"}),
}


PYTHON_STOPS = frozenset({"--", "-h", "--help", "-V", "--version"})


SHELL_PREFIXES = {
    "!",
    "command",
    "do",
    "elif",
    "else",
    "exec",
    "if",
    "then",
    "time",
}


SHELL_NON_EXECUTABLES = {
    "[",
    "[[",
    "break",
    "case",
    "cd",
    "continue",
    "declare",
    "done",
    "echo",
    "esac",
    "eval",
    "exit",
    "export",
    "false",
    "fi",
    "for",
    "local",
    "printf",
    "read",
    "readonly",
    "return",
    "set",
    "shift",
    "shopt",
    "source",
    "test",
    "trap",
    "true",
    "typeset",
    "ulimit",
    "umask",
    "unset",
    "until",
    "wait",
    "while",
}


UV_RUN_OPTIONS_WITH_VALUE = frozenset(
    {
        "--cache-dir",
        "--config-file",
        "--config-setting",
        "--directory",
        "--env-file",
        "--exclude-newer",
        "--group",
        "--index",
        "--link-mode",
        "--package",
        "--project",
        "--python",
        "--resolution",
        "--with",
    }
)


NPX_OPTIONS_WITH_VALUE = frozenset({"--cache", "--call", "--package", "-c", "-p"})


UVX_OPTIONS_WITH_VALUE = frozenset({"--from", "--index", "--python", "--refresh-package", "--with"})


NPM_OPTIONS_WITH_VALUE = frozenset({"--prefix", "--workspace", "-w"})


ENV_OPTIONS_WITH_VALUE = frozenset({"--chdir", "--unset", "-C", "-u"})
