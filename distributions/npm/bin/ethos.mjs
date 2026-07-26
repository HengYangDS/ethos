#!/usr/bin/env node
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url)), ARGS = process.argv.slice(2);

function parentOf(path) {
  const parent = dirname(path);
  return parent === path ? null : parent;
}

function commandExists(command) {
  const probe =
    process.platform === "win32"
      ? spawnSync("where", [command], { encoding: "utf8" })
      : spawnSync("sh", ["-c", `command -v ${command}`], { encoding: "utf8" });
  return probe.status === 0;
}

function findSourceRoot(start) {
  let current = resolve(start);
  while (current) {
    if (
      resolve(current, "distributions", "npm", "bin") === SCRIPT_DIR &&
      existsSync(resolve(current, "pyproject.toml")) &&
      existsSync(resolve(current, "packages", "ethos", "pyproject.toml"))
    ) {
      return current;
    }
    current = parentOf(current);
  }
  return null;
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd || process.cwd(),
    env: process.env,
    stdio: options.stdio || "inherit",
    encoding: "utf8",
  });
  if (result.error && result.error.code === "ENOENT") {
    return { missing: true, status: 127, stderr: "" };
  }
  return {
    missing: false,
    status: result.status === null ? 1 : result.status,
    stderr: result.stderr || "",
  };
}

function pythonHasEthos(command) {
  const probe = spawnSync(
    command,
    [
      "-P",
      "-c",
      "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('ethos.cli') else 1)",
    ],
    {
      cwd: process.cwd(),
      env: process.env,
      stdio: "ignore",
      encoding: "utf8",
    }
  );
  return probe.status === 0;
}

const sourceRoot = findSourceRoot(SCRIPT_DIR);
if (sourceRoot && commandExists("uv")) {
  const result = run("uv", [
    "run",
    "--project",
    sourceRoot,
    "--package",
    "ethos",
    "ethos",
    ...ARGS,
  ]);
  process.exit(result.status);
}

for (const python of ["python3", "python"]) {
  if (!commandExists(python)) {
    continue;
  }
  if (!pythonHasEthos(python)) {
    continue;
  }
  const result = run(python, ["-P", "-m", "ethos.cli", ...ARGS]);
  process.exit(result.status);
}

console.error(
  [
    "ETHOS Python command plane was not found.",
    "Run this launcher from an ETHOS source checkout with uv installed,",
    "or install the Python package that provides `python -m ethos.cli`.",
  ].join(" ")
);
process.exit(127);
