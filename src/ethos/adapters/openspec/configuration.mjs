/** Observe and initialize configuration through the selected official OpenSpec package. */
import { createHash } from "node:crypto";
import { lstatSync, readFileSync, realpathSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { pathToFileURL } from "node:url";

const [entry, expectedVersion, root, mode] = process.argv.slice(2);
const packageRoot = realpathSync(path.resolve(path.dirname(entry), ".."));
const require = createRequire(pathToFileURL(entry));
const load = (relative) => import(new URL("../dist/" + relative, pathToFileURL(entry)));
const { parse } = await import(pathToFileURL(require.resolve("yaml")));
const { readProjectConfig, resolveConfigFilePath, validateConfigRules, classifyOpenSpecDir } =
  await load("core/project-config.js");
const { resolveOpenSpecRoot } = await load("core/root-selection.js");
const { serializeConfig } = await load("core/config-prompts.js");
const { DEFAULT_OPENSPEC_SCHEMA, OPENSPEC_CONFIG_YAML, OPENSPEC_CONFIG_YML } =
  await load("core/openspec-root.js");
const { resolveSchema, getSchemaDir, listSchemas, listSchemasWithInfo } = await load(
  "core/artifact-graph/resolver.js",
);
const { loadTemplate } = await load("core/artifact-graph/instruction-loader.js");
const digest = (value) => createHash("sha256").update(value).digest("hex");
const inputs = new Map();
const warnings = [];
console.warn = (...values) => warnings.push(values.join(" "));
console.error = (...values) => warnings.push(values.join(" "));
const result = {
  path: path.join(root, OPENSPEC_CONFIG_YAML),
  content: null,
  exists: false,
  safe: true,
  default_content: serializeConfig({ schema: DEFAULT_OPENSPEC_SCHEMA }),
  verdict: "pass",
  required_gaps: [],
  warnings,
  keys: [],
  context: "",
  rules: {},
  inputs: [],
};

function nativeBinding(relative) {
  let current = root;
  const parts = relative.split("/");
  for (const [index, part] of parts.entries()) {
    current = path.join(current, part);
    let info;
    try {
      info = lstatSync(current);
    } catch (error) {
      if (error.code === "ENOENT") return;
      throw error;
    }
    if (
      info.isSymbolicLink() ||
      (index < parts.length - 1 ? !info.isDirectory() : !info.isFile())
    ) {
      result.path = path.join(root, relative);
      result.exists = true;
      result.safe = false;
      throw new Error("openspec_config_unsafe_path");
    }
  }
}

function identity(file) {
  const actual = realpathSync(file);
  for (const [prefix, base] of [
    ["package", packageRoot],
    ["repository", root],
  ]) {
    const relative = path.relative(base, actual);
    if (!relative.startsWith(".." + path.sep) && relative !== ".." && !path.isAbsolute(relative)) {
      return prefix + ":" + relative.split(path.sep).join("/");
    }
  }
  throw new Error("openspec_config_external_material");
}

function material(file) {
  const id = identity(file);
  const bytes = readFileSync(file);
  inputs.set(file, { path: id, sha256: digest(bytes) });
  return bytes;
}

try {
  const metadata = JSON.parse(readFileSync(path.join(packageRoot, "package.json"), "utf8"));
  const { program } = await import(pathToFileURL(require.resolve("@fission-ai/openspec")));
  if (
    metadata.name !== "@fission-ai/openspec" ||
    metadata.version !== expectedVersion ||
    program.version() !== expectedVersion
  ) {
    throw new Error("openspec_effective_version_mismatch");
  }
  nativeBinding(OPENSPEC_CONFIG_YAML);
  nativeBinding(OPENSPEC_CONFIG_YML);
  const selected = resolveConfigFilePath(root);
  result.exists = selected !== null;
  if (selected) {
    result.path = selected;
    result.content = new TextDecoder("utf-8", { fatal: true }).decode(material(selected));
  } else if (mode !== "initialize") {
    result.required_gaps.push("openspec_config_missing");
  }
  const raw = parse(result.content ?? result.default_content);
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    result.required_gaps.push("openspec_config_not_mapping", "openspec_config_schema_missing");
  } else {
    result.keys = Object.keys(raw);
    const config = selected ? readProjectConfig(root) : raw;
    if (!config?.schema || typeof config.schema !== "string" || !config.schema.trim()) {
      result.required_gaps.push("openspec_config_schema_missing");
    } else {
      if (selected) {
        const home = classifyOpenSpecDir(root);
        if (!home.hasPlanningShape && home.pointer.value !== undefined) {
          result.required_gaps.push("openspec_config_external_store_unsupported");
        } else {
          await resolveOpenSpecRoot({ startPath: root, allowImplicitRoot: false });
        }
      }
      const directory = getSchemaDir(config.schema, root);
      if (directory) material(path.join(directory, "schema.yaml"));
      const schema = resolveSchema(config.schema, root);
      const ids = new Set(schema.artifacts.map((artifact) => artifact.id));
      if (Object.keys(config.rules ?? {}).some((id) => !ids.has(id))) {
        for (const name of listSchemas(root)) {
          const candidate = getSchemaDir(name, root);
          if (candidate) material(path.join(candidate, "schema.yaml"));
        }
        for (const candidate of listSchemasWithInfo(root)) {
          for (const id of candidate.artifacts) ids.add(id);
        }
      }
      warnings.push(...validateConfigRules(config.rules ?? {}, ids));
      for (const artifact of schema.artifacts) {
        const file = path.join(directory, "templates", artifact.template);
        material(file);
        loadTemplate(config.schema, artifact.template, root);
      }
      result.schema = config.schema;
      result.context = config.context ?? "";
      result.rules = config.rules ?? {};
    }
  }
  for (const [file, input] of inputs) {
    if (identity(file) !== input.path || digest(readFileSync(file)) !== input.sha256) {
      result.verdict = "unknown";
      result.required_gaps.push("openspec_config_inputs_changed");
    }
  }
} catch (error) {
  const unavailable = ["EACCES", "EPERM", "EIO", "ESTALE"].includes(error.code);
  result.verdict = unavailable ? "unknown" : "block";
  result.required_gaps.push(
    unavailable
      ? "openspec_config_unavailable:" + error.code
      : error.message.startsWith("openspec_")
        ? error.message
        : "openspec_config_invalid:" + (error.diagnostic?.code ?? error.name),
  );
  result.detail = String(error);
}
if (warnings.length) result.required_gaps.push("openspec_config_native_warning");
if (result.required_gaps.length && result.verdict === "pass") result.verdict = "block";
result.inputs = [...inputs.values()].sort((a, b) =>
  a.path < b.path ? -1 : a.path > b.path ? 1 : 0,
);
result.input_digest = digest(
  JSON.stringify({
    version: expectedVersion,
    path: path.relative(root, result.path).split(path.sep).join("/"),
    exists: result.exists,
    default_content: result.default_content,
    inputs: result.inputs,
  }),
);
process.stdout.write(JSON.stringify(result));
