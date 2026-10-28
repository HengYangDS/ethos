import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { chmodSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

function temporary(t, prefix) {
  const directory = mkdtempSync(join(tmpdir(), prefix));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  return directory;
}

test("the launcher package exposes only its declared transport", (t) => {
  const cache = temporary(t, "ethos-launcher-npm-");
  const result = spawnSync(
    process.execPath,
    [process.env.npm_execpath, "pack", "--dry-run", "--json", join(ROOT, "distributions/npm")],
    {
      cwd: ROOT,
      encoding: "utf8",
      timeout: 30000,
      env: { ...process.env, npm_config_cache: cache, npm_config_offline: "true" },
    },
  );
  assert.equal(result.status, 0, result.stderr);
  const packages = Object.values(JSON.parse(result.stdout));
  assert.equal(packages.length, 1);
  assert.deepEqual(packages[0].files.map(({ path }) => path).sort(), [
    "README.md",
    "bin/ethos.mjs",
    "package.json",
  ]);
});

// The launcher finds uv and Python by name, so a PATH of stubs records the command it chooses.
function launch(t, stubs) {
  const bin = temporary(t, "ethos-launcher-bin-");
  symlinkSync("/bin/sh", join(bin, "sh"));
  for (const [name, body] of Object.entries(stubs)) {
    writeFileSync(join(bin, name), `#!/bin/sh\n${body}\n`);
    chmodSync(join(bin, name), 0o755);
  }
  const { NODE_OPTIONS: _options, ...env } = process.env;
  return spawnSync(process.execPath, [join(ROOT, "distributions/npm/bin/ethos.mjs"), "--version"], {
    cwd: temporary(t, "ethos-launcher-cwd-"),
    encoding: "utf8",
    timeout: 30000,
    env: { ...env, PATH: bin },
  });
}

const posix = { skip: process.platform === "win32" && "the stubs are POSIX shell scripts" };

test("a source checkout runs the command through uv", posix, (t) => {
  const result = launch(t, { uv: 'printf "%s\\n" "$@"; exit 7' });
  assert.equal(result.status, 7, result.stderr);
  assert.deepEqual(result.stdout.trimEnd().split("\n"), [
    "run",
    "--project",
    ROOT,
    "ethos",
    "--version",
  ]);
});

test("an installed package runs the command through Python", posix, (t) => {
  const result = launch(t, { python3: 'if [ "$2" = -c ]; then exit 0; fi; printf "%s\\n" "$@"' });
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(result.stdout.trimEnd().split("\n"), ["-P", "-m", "ethos.cli", "--version"]);
});

test("without a command plane the launcher names what is missing", posix, (t) => {
  const result = launch(t, { python3: "exit 1", python: "exit 1" });
  assert.equal(result.status, 127);
  assert.match(result.stderr, /^ETHOS Python command plane was not found\./);
});
