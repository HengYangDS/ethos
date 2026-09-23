/** Shared isolated Publisher package fixtures and explicit source inputs. */
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import fs from "node:fs/promises";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

export const sha256 = (value) => createHash("sha256").update(value).digest("hex");

export function stable(value) {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  return `{${Object.keys(value)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${stable(value[key])}`)
    .join(",")}}`;
}

export async function selectedArchive(name) {
  const selected = process.env[name];
  assert.equal(path.isAbsolute(selected ?? ""), true, `${name} must be an absolute path`);
  const stat = await fs.lstat(selected);
  assert.equal(stat.isFile() && !stat.isSymbolicLink(), true, `${name} must be a regular file`);
  return selected;
}

export async function selectedPath(name, { directory = false } = {}) {
  const selected = process.env[name];
  assert.equal(path.isAbsolute(selected ?? ""), true, `${name} must be an absolute path`);
  const stat = await fs.lstat(selected);
  assert.equal(
    directory ? stat.isDirectory() : stat.isFile() && !stat.isSymbolicLink(),
    true,
    `${name} must identify the expected local input`,
  );
  return selected;
}

export async function installPackages(
  t,
  integrationArchiveVariable = "ETHOS_ARCHITECTURE_PUBLISHER_PACKAGE",
) {
  const coreArchive = await selectedArchive("ARCHITECTURE_PUBLISHER_PACKAGE");
  const ethosArchive = await selectedArchive(integrationArchiveVariable);
  const root = await fs.realpath(
    await fs.mkdtemp(path.join(tmpdir(), "ethos-architecture-publisher-installed-")),
  );
  t.after(() => fs.rm(root, { recursive: true, force: true }));
  const project = path.join(root, "consumer");
  const home = path.join(root, "home");
  const cache = path.join(root, "npm-cache");
  await fs.mkdir(project);
  await fs.mkdir(home);
  await fs.writeFile(
    path.join(project, "package.json"),
    JSON.stringify({ private: true, type: "module" }),
  );
  const installed = spawnSync(
    "npm",
    [
      "install",
      "--offline",
      "--ignore-scripts",
      "--no-audit",
      "--no-fund",
      "--package-lock=false",
      coreArchive,
      ethosArchive,
    ],
    {
      cwd: project,
      encoding: "utf8",
      env: {
        ...process.env,
        HOME: home,
        npm_config_cache: cache,
        npm_config_offline: "true",
        npm_config_registry: "https://registry.invalid/",
        npm_config_update_notifier: "false",
      },
    },
  );
  assert.equal(installed.status, 0, installed.stderr);
  const coreRoot = path.join(project, "node_modules", "architecture-publisher");
  const integrationRoot = path.join(project, "node_modules", "@architecture-publisher", "ethos");
  const resolvePackage = createRequire(path.join(project, "package.json")).resolve;
  const importPublic = async (specifier) => import(pathToFileURL(resolvePackage(specifier)).href);
  return {
    project,
    coreRoot,
    integrationRoot,
    importPublic,
    sourceApi: await importPublic("architecture-publisher/source"),
    adapter: await importPublic("@architecture-publisher/ethos/adapter"),
    edition: await importPublic("@architecture-publisher/ethos/edition"),
    runtime: await importPublic("@architecture-publisher/ethos/runtime"),
  };
}

export function fixture() {
  const commit = "1".repeat(40);
  const tree = "2".repeat(40);
  const graph = {
    schema: "synthetic",
    nodes: {},
    edges: [],
    invariants: [{ statement: "All attempts preserve scope" }],
  };
  const copy = { assertions: { maturity: { text: "Target design, not implementation" } } };
  const view = { node_projection: {}, omitted_nodes: {} };
  const quality = '{"schema":"synthetic-test-only","authority":{"consumers_may_override":false}}\n';
  const selected = {
    copy: "system/copy.json",
    quality_contract: "system/quality.json",
    semantic_graph: "system/graph.json",
    view_profile: "system/view.json",
  };
  const contents = {
    "docs/contract.md": Buffer.from("All attempts MAY retry only after transient failure.\n"),
    "system/copy.json": Buffer.from(JSON.stringify(copy)),
    "system/quality.json": Buffer.from(quality),
    "system/graph.json": Buffer.from(JSON.stringify(graph)),
    "system/view.json": Buffer.from(JSON.stringify(view)),
  };
  const binding = {
    id: "contract",
    path: "docs/contract.md",
    sha256: sha256(contents["docs/contract.md"]),
    authority: "synthetic test meaning",
  };
  const declaration = {
    schema: "ethos.projection-declaration/v1",
    id: "synthetic-ethos-contract",
    title: "Synthetic contract",
    authority: {
      semantic_owner: "docs/contract.md",
      scope: "test only",
      effect_authority: false,
    },
    sources: [{ id: binding.id, path: binding.path, authority: binding.authority }],
    documents: selected,
  };
  const input = {
    schema: "projection.input/v2",
    title: declaration.title,
    authority: declaration.authority,
    source: {
      id: declaration.id,
      revision: commit,
      git: { commit, tree },
      bindings: [binding],
      documents: Object.entries(selected).map(([id, sourcePath]) => ({
        id,
        path: sourcePath,
        sha256: sha256(contents[sourcePath]),
      })),
    },
    documents: { copy, view_profile: view, quality_contract: quality },
    semantics: {
      nodes: {
        attempt: {
          label: "Attempt",
          kind: "subject",
          attributes: { quantifier: "All", maturity: "target" },
          provenance: ["contract"],
        },
      },
      relations: [
        {
          id: "retry",
          from: "attempt",
          to: "attempt",
          kind: "retry",
          attributes: { condition: "transient failure", quantifier: "Any", scope: "attempt" },
          provenance: ["contract"],
        },
      ],
      contracts: { invariants: graph.invariants },
    },
    view: {
      nodes: { attempt: { project: { witness: "maturity" } } },
      relations: { retry: { project: { witness: "maturity" } } },
    },
  };
  const members = [
    { path: "source/LICENSE", content: Buffer.from("Synthetic fixture license notice\n") },
    { path: "projection-input.json", content: Buffer.alloc(0) },
    {
      path: "source/system/projections/terminal-architecture/declaration.json",
      content: Buffer.from(JSON.stringify(declaration)),
    },
    {
      path: "source/tools/projection/export_terminal_architecture.py",
      content: Buffer.from("# Synthetic exporter fixture; never official ETHOS evidence\n"),
    },
    {
      path: "source/src/ethos/repository/policy/projections.py",
      content: Buffer.from("# Synthetic policy owner fixture\n"),
    },
    ...Object.entries(contents).map(([memberPath, content]) => ({
      path: `source/${memberPath}`,
      content,
    })),
  ];
  const refresh = () => {
    delete input.digest;
    input.digest = sha256(`${stable(input)}\n`);
    members.find(({ path: memberPath }) => memberPath === "projection-input.json").content =
      Buffer.from(JSON.stringify(input));
  };
  refresh();
  return { input, members, refresh, source: { id: input.source.id, revision: commit } };
}
