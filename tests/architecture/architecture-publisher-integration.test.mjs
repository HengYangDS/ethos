import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtempSync, readFileSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const INTEGRATION = join(ROOT, "integrations", "architecture-publisher");

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function moduleFiles(root) {
  return readdirSync(root, { recursive: true, withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(".mjs"))
    .map((entry) => join(entry.parentPath, entry.name))
    .sort();
}

test("the integration is optional and imports only Publisher public contracts", () => {
  const packageManifest = readJson(join(INTEGRATION, "package.json"));
  const workspace = readJson(join(ROOT, "package.json"));

  assert.equal(packageManifest.name, "@architecture-publisher/ethos");
  assert.equal(packageManifest.version, "0.2.0-alpha.0");
  assert.deepEqual(packageManifest.exports, {
    "./adapter": "./src/adapter/index.mjs",
    "./edition": "./src/edition/index.mjs",
    "./runtime": "./src/runtime.mjs",
  });
  assert.deepEqual(packageManifest.dependencies, {
    "architecture-publisher": "0.2.0-alpha.0",
  });
  assert.equal("bin" in packageManifest, false);
  assert.equal(workspace.workspaces.includes("integrations/architecture-publisher"), false);

  const imports = /\bfrom\s+['"]([^'"]+)['"]/g;
  for (const source of moduleFiles(join(INTEGRATION, "src"))) {
    const content = readFileSync(source, "utf8");
    assert.equal(content.includes("/Users/"), false, relative(ROOT, source));
    for (const match of content.matchAll(imports)) {
      assert.equal(
        match[1].startsWith(".") ||
          match[1].startsWith("node:") ||
          match[1].startsWith("architecture-publisher"),
        true,
        `${relative(ROOT, source)} imports ${match[1]}`,
      );
    }
  }
});

test("the migration baseline binds exact Publisher and ETHOS inputs", () => {
  const baseline = readJson(join(INTEGRATION, "migration-baseline.json"));

  assert.deepEqual(baseline, {
    schema: "ethos.architecture-publisher-migration-baseline/v1",
    publisher: {
      repository: "dig/research/human-agent-stewardship/architecture-publisher",
      commit: "7652d83251ebd33d44a21e935e56972d41482599",
      migrationTree: "de973462a508c8d213c5ac1143cd52d8bd9576bb",
      sourceTree: "e20c22d5a500b5c3c9498671e1dac95daddd72ea",
      packageBlob: "6ff2d3dbf52884594e3ff6d662baccf855ea5671",
      packageSha256: "d15730c160820874faa7564e79c28747e391f306e6192a50a42d5238f899646d",
      package: {
        name: "@architecture-publisher/ethos",
        version: "0.2.0-alpha.0",
      },
    },
    ethos: {
      acceptedCommit: "9a34b12ab1e30bab69ad8c28a15f657c903027c4",
      projectionTree: "21da3725e51c6da0fa4a6380be7fec50c915e646",
      declarationBlob: "805d9974992eb4cce08d3ced67d14cc28347cfdb",
      declarationSha256: "401ea8938a4a847082c9d50f0cacf9cefe6aec3b9a6d8facf1b16d78e8e3ecc6",
      editionSource: {
        commit: "8f2e829fed3877c5375cd8636bea45bee583f6c4",
        projectionDigest: "4ea40f421434106948f1e1d2d9ae5ee6c8b9868edc5538ff755876fd01d37ef8",
        sourceManifestSha256: "58121ad168a314af94b55f557435ffb7d9828ca7c476411f18467731ae9d1db0",
        exporterSha256: "f32780b5135523e209749e3f8651dbd152f63baa68329a270956586a5bfa6520",
        ownerSha256: "158e26f07f1827c376c2fbf8116f84c0be8bcf2dae4972ee4c038cc2fa85918e",
      },
      acceptedProjection: {
        commit: "9a34b12ab1e30bab69ad8c28a15f657c903027c4",
        projectionDigest: "36bae59c26be802222db569d5594216f059115bceab40dc17f20de72f1447b98",
        exporterSha256: "f32780b5135523e209749e3f8651dbd152f63baa68329a270956586a5bfa6520",
        ownerSha256: "4dcc6862f5b43bfe53ab1a3f9b80ef30aeb6ebd636226afa3f4876d37620a283",
      },
    },
    scope:
      "Exact migration inputs only; no generated artifact, acceptance, publication, or off-host recovery claim.",
  });
  assert.equal(sha256(join(INTEGRATION, "package.json")), baseline.publisher.packageSha256);
});

test("the optional package contains only its declared source-owned delivery", (t) => {
  const cache = mkdtempSync(join(tmpdir(), "ethos-architecture-publisher-npm-"));
  t.after(() => rmSync(cache, { recursive: true, force: true }));
  const result = spawnSync("npm", ["pack", "--dry-run", "--json", INTEGRATION], {
    cwd: ROOT,
    encoding: "utf8",
    env: { ...process.env, npm_config_cache: cache, npm_config_update_notifier: "false" },
  });
  assert.equal(result.status, 0, result.stderr);
  const [packed] = JSON.parse(result.stdout);
  const files = packed.files.map(({ path }) => path);

  assert.equal(packed.id, "@architecture-publisher/ethos@0.2.0-alpha.0");
  assert.equal(files.includes("package.json"), true);
  assert.equal(files.includes("README.md"), true);
  assert.equal(files.includes("src/runtime.mjs"), true);
  assert.equal(files.includes("src/edition/authoring/edition.json"), true);
  assert.equal(files.includes("migration-baseline.json"), false);
  assert.equal(
    files.some((path) => path.startsWith("tests/")),
    false,
  );
});

test("the runtime identity closes over only the explicitly installed package", async () => {
  const { readEthosExtensionRuntime } =
    await import("../../integrations/architecture-publisher/src/runtime.mjs");
  const first = await readEthosExtensionRuntime();
  const second = await readEthosExtensionRuntime();

  assert.deepEqual(second, first);
  assert.deepEqual(
    first.map(({ path }) => path),
    first.map(({ path }) => path).toSorted(),
  );
  assert.equal(new Set(first.map(({ path }) => path)).size, first.length);
  assert.equal(
    first.some(({ path }) => path === "package.json"),
    true,
  );
  assert.equal(
    first.some(({ path }) => path === "src/runtime.mjs"),
    true,
  );
  for (const member of first) {
    assert.equal(isAbsolute(member.path), false);
    assert.equal(member.path === "package.json" || member.path.startsWith("src/"), true);
    assert.equal(member.file.startsWith(`${resolve(INTEGRATION)}/`), true);
    assert.match(member.sha256, /^[0-9a-f]{64}$/);
    assert.equal(Number.isSafeInteger(member.bytes) && member.bytes >= 0, true);
  }
});
