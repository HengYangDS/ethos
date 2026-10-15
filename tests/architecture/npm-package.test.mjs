import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

test("the launcher package exposes only its declared transport", (t) => {
  const cache = mkdtempSync(join(tmpdir(), "ethos-launcher-npm-"));
  t.after(() => rmSync(cache, { recursive: true, force: true }));
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
