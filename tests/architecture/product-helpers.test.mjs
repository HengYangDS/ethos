import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdirSync, mkdtempSync, readFileSync, realpathSync, rmSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import test from "node:test";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const SUPPLY = process.env.ETHOS_NODE_PACKAGE_SUPPLY ?? join(ROOT, "node_modules");
const NPM = join(SUPPLY, "npm/bin/npm-cli.js");
const OPENSPEC = join(SUPPLY, "@fission-ai/openspec/bin/openspec.js");
const OPENSPEC_VERSION = JSON.parse(
  readFileSync(join(SUPPLY, "@fission-ai/openspec/package.json"), "utf8"),
).version;

// The product callers remove these, and an inherited test context would nest the runner.
const REMOVED = new Set(["NODE_OPTIONS", "NODE_PATH", "NODE_TEST_CONTEXT"]);
const INHERITED = Object.fromEntries(
  Object.entries(process.env).filter(([name]) => !REMOVED.has(name)),
);

// Helpers judge canonical paths, so a scratch root is canonical too.
function scratch(t) {
  const directory = realpathSync(mkdtempSync(join(tmpdir(), "ethos-helper-")));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  return directory;
}

function write(root, files) {
  for (const [relative, content] of Object.entries(files)) {
    mkdirSync(dirname(join(root, relative)), { recursive: true });
    writeFileSync(join(root, relative), content);
  }
}

function run(args, { input = "", cwd = ROOT, env = {} } = {}) {
  return spawnSync(process.execPath, args, {
    cwd,
    env: { ...INHERITED, ...env },
    input,
    encoding: "utf8",
    timeout: 60000,
  });
}

function helper(relative, args, options) {
  return run([join(ROOT, "src/ethos/adapters", relative), ...args], options);
}

// OpenSpec reads its home and telemetry settings; its product callers isolate both.
function openspec(home) {
  return {
    HOME: home,
    XDG_CONFIG_HOME: home,
    XDG_DATA_HOME: home,
    OPENSPEC_TELEMETRY: "0",
    OPENSPEC_NO_UPDATE_CHECK: "1",
    TZ: "UTC",
  };
}

function project(t) {
  const home = scratch(t);
  const root = join(home, "repository");
  write(root, {
    "openspec/config.yaml": "schema: spec-driven\n",
    "openspec/specs/.keep": "",
    "openspec/changes/sample/.openspec.yaml": "schema: spec-driven\n",
    "openspec/changes/sample/proposal.md": "# Proposal\n",
    "openspec/changes/sample/tasks.md": "## 1. Work\n\n- [ ] 1.1 Do the work\n",
  });
  return { home, root };
}

test("analysis lints exact sources with the recommended rules of each declared environment", () => {
  const entries = [
    ["clean.mjs", "export const answer = 42;\n", []],
    ["browser.mjs", "export const width = window.innerWidth;\n", ["browser"]],
    ["undefined.mjs", "export const answer = missing;\n", []],
  ].map(([path, source, environments]) => ({ path, source, sourceType: "module", environments }));
  const result = helper("gates/javascript/analysis.mjs", [join(SUPPLY, "eslint/package.json")], {
    input: JSON.stringify(entries),
  });
  assert.equal(result.status, 1, result.stderr);
  const reports = JSON.parse(result.stdout);
  assert.deepEqual(
    reports.map(({ filePath, errorCount }) => [filePath, errorCount]),
    entries.map(({ path }, index) => [join(ROOT, path), index === 2 ? 1 : 0]),
  );
  assert.deepEqual(
    reports[2].messages.map(({ ruleId }) => ruleId),
    ["no-undef"],
  );
});

test("selection keeps the production paths that c8 would report", (t) => {
  const result = helper(
    "gates/javascript/selection.mjs",
    [join(SUPPLY, "c8/bin/c8.js"), "--include=src/**/*.mjs"],
    {
      cwd: scratch(t),
      input: JSON.stringify(["src/kept.mjs", "src/kept.test.mjs", "lib/dropped.mjs"]),
    },
  );
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout), {
    config: null,
    all: false,
    selected_paths: ["src/kept.mjs"],
  });
});

test("the reporter writes every test event as one JSON line, errors included", async () => {
  const reporter = pathToFileURL(join(ROOT, "src/ethos/adapters/gates/javascript/reporter.mjs"));
  const { default: report } = await import(reporter);
  const cause = new TypeError("expected failure");
  const failure = Object.assign(new Error("test failed", { cause }), { code: "ERR_TEST_FAILURE" });
  async function* events() {
    yield { type: "test:pass", data: { name: "passes" } };
    yield { type: "test:fail", data: { name: "fails", details: { error: failure } } };
  }
  const lines = [];
  for await (const line of report(events())) lines.push(line);
  assert.ok(lines.every((line) => /^[^\n]+\n$/.test(line)));
  const [passed, failed] = lines.map((line) => JSON.parse(line));
  assert.deepEqual(passed, { type: "test:pass", data: { name: "passes" } });
  const { error } = failed.data.details;
  assert.deepEqual(
    [error.code, error.name, error.message, error.cause.name, error.cause.message],
    ["ERR_TEST_FAILURE", "Error", "test failed", "TypeError", "expected failure"],
  );
  assert.match(error.stack, /^Error: test failed\n/);
});

test("markdown lint judges exact content by the explicit native policy", (t) => {
  const directory = scratch(t);
  write(directory, {
    ".markdownlint.json": '{"default": true}\n',
    "clean.md": "# Title\n",
    "broken.md": "#Title\n",
  });
  const lint = (selected) =>
    helper("gates/markdown.mjs", [
      join(SUPPLY, "markdownlint-cli2/markdownlint-cli2.mjs"),
      join(directory, ".markdownlint.json"),
      directory,
      JSON.stringify(selected),
    ]);
  const clean = lint(["clean.md"]);
  assert.equal(clean.status, 0, clean.stderr);
  const broken = lint(["broken.md"]);
  assert.equal(broken.status, 1);
  assert.match(broken.stderr, /broken\.md:1(?::\d+)? error MD018/);
});

test("archive observation matches exact member bytes in a locked tarball", (t) => {
  const directory = scratch(t);
  const manifest = '{"name":"sample","version":"1.0.0"}\n';
  write(directory, { "package/package.json": manifest });
  const tarball = join(directory, "sample.tgz");
  createRequire(NPM)("tar").c(
    { gzip: true, sync: true, portable: true, file: tarball, cwd: directory },
    ["package/package.json"],
  );
  const bytes = readFileSync(tarball);
  const limits = {
    archive_bytes: 1 << 20,
    raw_bytes: 1 << 20,
    input_bytes: 1 << 22,
    expanded_bytes: 1 << 20,
    metadata_bytes: 1 << 16,
    entries: 16,
    digests: 4,
  };
  const observe = (expected, overrides = {}) =>
    helper("gates/provenance/archive.mjs", [NPM], {
      input: JSON.stringify({
        limits: { ...limits, ...overrides },
        archives: [
          {
            data: bytes.toString("base64"),
            integrity: `sha512-${createHash("sha512").update(bytes).digest("base64")}`,
            members: {
              manifest: {
                member: "package/package.json",
                expected: Buffer.from(expected).toString("base64"),
              },
            },
          },
        ],
      }),
    });
  const matched = observe(manifest);
  assert.equal(matched.status, 0, matched.stderr);
  assert.deepEqual(JSON.parse(matched.stdout), { matched: ["manifest"] });
  for (const [expected, overrides, reason] of [
    ["{}\n", {}, "archive_member_bytes_mismatch"],
    [manifest, { entries: 0 }, "archive_limits_invalid"],
  ]) {
    const refused = observe(expected, overrides);
    assert.deepEqual([refused.status, refused.stdout, refused.stderr], [1, "", reason]);
  }
});

test("the OpenSpec batch runs native reads in order and refuses another version", (t) => {
  const { home, root } = project(t);
  const batch = (version, commands) =>
    helper("openspec/batch.mjs", [OPENSPEC, "30", version], {
      cwd: root,
      env: openspec(home),
      input: JSON.stringify(commands),
    });
  const status = ["status", "--change", "sample", "--json"];
  const result = batch(OPENSPEC_VERSION, [status]);
  assert.equal(result.status, 0, result.stderr);
  const [row, ...rest] = result.stdout
    .trimEnd()
    .split("\n")
    .map((line) => JSON.parse(line));
  assert.deepEqual(rest, []);
  assert.deepEqual([row.index, row.args, row.stderr, row.exit_code], [0, status, "", 0]);
  assert.equal(JSON.parse(row.stdout).changeName, "sample");
  assert.deepEqual(
    [row.task_tracking.configured, row.task_tracking.artifactId, row.task_tracking.outputPaths],
    [true, "tasks", [join(row.task_tracking.changeRoot, "tasks.md")]],
  );
  const other = batch("0.0.0", [status]);
  assert.deepEqual(
    [other.status, other.stdout, other.stderr],
    [1, "", "openspec_effective_version_mismatch\n"],
  );
});

test("OpenSpec configuration binds its native inputs and refuses an unsafe carrier", (t) => {
  const { home, root } = project(t);
  const observe = (directory) =>
    JSON.parse(
      helper("openspec/configuration.mjs", [OPENSPEC, OPENSPEC_VERSION, directory, "inspect"], {
        env: openspec(home),
      }).stdout,
    );
  const present = observe(root);
  assert.deepEqual(
    [present.verdict, present.required_gaps, present.exists, present.schema],
    ["pass", [], true, "spec-driven"],
  );
  assert.ok(present.inputs.some(({ path }) => path === "repository:openspec/config.yaml"));
  const absent = join(home, "absent");
  mkdirSync(absent);
  assert.deepEqual(
    Object.values(
      (({ verdict, required_gaps, exists, path }) => ({ verdict, required_gaps, exists, path }))(
        observe(absent),
      ),
    ),
    ["block", ["openspec_config_missing"], false, join(absent, "openspec/config.yaml")],
  );
  // A configuration carrier must be a regular file.
  const occupied = join(home, "occupied");
  mkdirSync(join(occupied, "openspec/config.yaml"), { recursive: true });
  const unsafe = observe(occupied);
  assert.deepEqual(
    [unsafe.verdict, unsafe.required_gaps, unsafe.safe],
    ["block", ["openspec_config_unsafe_path"], false],
  );
});

test("relocation keeps a moved document's references on their targets", () => {
  const before = "openspec/changes/sample/design.md";
  const after = "openspec/changes/archive/2026-10-28-sample/design.md";
  const relocate = (content) =>
    helper("openspec/relocation.mjs", [OPENSPEC], {
      input: JSON.stringify({
        files: { [before]: "100644", "openspec/specs/quality/spec.md": "100644" },
        postimage_files: { [after]: "100644", "openspec/specs/quality/spec.md": "100644" },
        moves: [["openspec/changes/sample", "openspec/changes/archive/2026-10-28-sample"]],
        documents: [{ before, after, content }],
        canonical: [],
      }),
    });
  const moved = relocate("See [the spec](../../specs/quality/spec.md).\n");
  assert.equal(moved.status, 0, moved.stderr);
  assert.deepEqual(JSON.parse(moved.stdout), {
    documents: [{ path: after, content: "See [the spec](../../../specs/quality/spec.md).\n" }],
    canonical: [],
  });
  const missing = relocate("See [the spec](../../specs/absent/spec.md).\n");
  assert.equal(missing.status, 1);
  assert.match(
    missing.stderr,
    new RegExp(
      `^Error: archive_reference_target_missing:${before}:openspec/specs/absent/spec\\.md$`,
      "m",
    ),
  );
});
