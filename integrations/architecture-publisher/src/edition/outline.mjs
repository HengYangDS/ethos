import fs from "node:fs/promises";
import { constants } from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { fail, isDigest } from "architecture-publisher/source";
import { writeSourceBundle } from "architecture-publisher/source";
import { fileIdentity } from "architecture-publisher/renderers/svg";
import { validateSvg } from "architecture-publisher/renderers/resvg";
import { RASTER_LIMITS as limits } from "architecture-publisher/renderers/resvg";
import { renderEthosPoster } from "./poster.mjs";

const sha = (b) => createHash("sha256").update(b).digest("hex");
const encode = (x) => Buffer.from(JSON.stringify(x, null, 2) + "\n");
const fields = (v, keys) =>
  v &&
  typeof v === "object" &&
  !Array.isArray(v) &&
  Object.keys(v).length === keys.length &&
  keys.every((k) => Object.hasOwn(v, k));
const absolute = (p) => typeof p === "string" && path.isAbsolute(p);
const xml = (s) => s.replaceAll("&", "&amp;").replaceAll("<", "&lt;");

/** Optional host conversion; preserves source and exposes changed-pixel scope. */
export async function outlineEthosPoster(plan) {
  if (
    !fields(plan, ["poster", "renderer", "fontList", "fonts", "reference", "output"]) ||
    !fields(plan.poster, [
      "sourceManifest",
      "sourceSha256",
      "projectionDigest",
      "editionManifest",
      "editionSha256",
    ]) ||
    !fields(plan.reference, ["width", "height", "pngSha256"]) ||
    !isDigest(plan.reference.pngSha256) ||
    !absolute(plan.output) ||
    !Array.isArray(plan.fonts) ||
    !plan.fonts.length ||
    plan.fonts.length > 16
  )
    fail("outline_plan_invalid");
  for (const k of ["renderer", "fontList"])
    if (
      !fields(plan[k], ["path", "sha256"]) ||
      !absolute(plan[k].path) ||
      !isDigest(plan[k].sha256)
    )
      fail("outline_plan_invalid");
  for (const f of plan.fonts)
    if (!fields(f, ["path", "sha256"]) || !absolute(f.path) || !isDigest(f.sha256))
      fail("outline_plan_invalid");
  const { width, height } = plan.reference;
  if (
    !Number.isSafeInteger(width) ||
    !Number.isSafeInteger(height) ||
    width < 1 ||
    height < 1 ||
    width > limits.width ||
    height > limits.height ||
    width * height > limits.pixels
  )
    fail("outline_plan_invalid");
  const parent = path.dirname(plan.output),
    stat = await fs.lstat(parent);
  if (!stat.isDirectory() || stat.isSymbolicLink() || (await fs.realpath(parent)) !== parent)
    fail("output_parent_invalid");
  try {
    await fs.lstat(plan.output);
    fail("output_exists");
  } catch (e) {
    if (e.code !== "ENOENT") throw e;
  }
  const tools = {};
  for (const name of ["renderer", "fontList"]) {
    tools[name] = await fileIdentity(
      plan[name].path,
      plan[name].sha256,
      512 * 1024 * 1024,
      "outline_tool_changed",
    );
    await fs.access(tools[name].path, constants.X_OK);
  }
  const fonts = [];
  for (const f of plan.fonts)
    fonts.push(await fileIdentity(f.path, f.sha256, 128 * 1024 * 1024, "outline_font_changed"));
  const fontPaths = new Set(fonts.map((f) => f.path));
  if (fontPaths.size !== fonts.length || fonts.reduce((n, f) => n + f.bytes, 0) > 256 * 1024 * 1024)
    fail("outline_plan_invalid");
  const scratch = await fs.mkdtemp(path.join(parent, ".architecture-outline-"));
  try {
    const poster = await renderEthosPoster({
      ...plan.poster,
      output: path.join(scratch, "poster"),
    });
    const source = await fs.readFile(path.join(scratch, "poster/terminal.svg"));
    const text = await fs.readFile(path.join(scratch, "poster/text.txt"));
    for (const n of ["fonts", "cache", "home"]) await fs.mkdir(path.join(scratch, n));
    for (const [i, f] of fonts.entries())
      await fs.symlink(f.path, path.join(scratch, "fonts", i + path.extname(f.path)));
    const configuration = `<?xml version="1.0"?><fontconfig><dir>${xml(scratch + "/fonts")}</dir><cachedir>${xml(scratch + "/cache")}</cachedir></fontconfig>`;
    await fs.writeFile(path.join(scratch, "fonts.conf"), configuration, {
      flag: "wx",
    });
    const env = {
      HOME: scratch + "/home",
      PATH: scratch + "/home",
      TMPDIR: scratch + "/home",
      TMP: scratch + "/home",
      TEMP: scratch + "/home",
      LANG: "C.UTF-8",
      FONTCONFIG_FILE: scratch + "/fonts.conf",
      FONTCONFIG_PATH: scratch,
    };
    function run(tool, args, input, maximum) {
      const r = spawnSync(tool, args, {
        input,
        cwd: scratch,
        env,
        timeout: limits.executionMs,
        maxBuffer: maximum,
      });
      if (r.error || r.signal || r.status !== 0)
        fail(
          r.error?.code === "ETIMEDOUT" ? "outline_execution_timeout" : "outline_execution_failed",
        );
      return r.stdout;
    }
    const listed = run(tools.fontList.path, ["-f", "%{file}\n"], undefined, 1024 * 1024)
      .toString("utf8")
      .trim()
      .split("\n");
    const seen = new Set();
    for (const file of listed) {
      if (!absolute(file)) fail("outline_font_inventory_mismatch");
      let resolved;
      try {
        resolved = await fs.realpath(file);
      } catch {
        fail("outline_font_inventory_mismatch");
      }
      if (!fontPaths.has(resolved)) fail("outline_font_inventory_mismatch");
      seen.add(resolved);
    }
    if (seen.size !== fonts.length) fail("outline_font_inventory_mismatch");
    const reference = run(tools.renderer.path, ["--width", String(width)], source, limits.pngBytes);
    if (
      reference.length < 33 ||
      sha(reference) !== plan.reference.pngSha256 ||
      !reference.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) ||
      reference.readUInt32BE(16) !== width ||
      reference.readUInt32BE(20) !== height
    )
      fail("outline_reference_mismatch");
    const outlined = run(tools.renderer.path, ["--format", "svg"], source, limits.svgBytes);
    const checked = validateSvg(outlined, [], width);
    if (
      checked.height !== height ||
      /<(?:[\w.-]+:)?(?:text|tspan)\b/.test(outlined.toString("utf8"))
    )
      fail("outline_not_font_free");
    for (const name of ["renderer", "fontList"])
      await fileIdentity(
        plan[name].path,
        tools[name].sha256,
        512 * 1024 * 1024,
        "outline_tool_changed",
      );
    for (const f of fonts)
      await fileIdentity(f.path, f.sha256, 128 * 1024 * 1024, "outline_font_changed");
    const result = {
      status: "outlined",
      source: poster.source,
      labels: poster.labels,
      sourceSvg: { sha256: sha(source), bytes: source.length },
      textSha256: sha(text),
      tools,
      fonts,
      reference: { width, height, sha256: sha(reference) },
      outlined: {
        sha256: sha(outlined),
        bytes: outlined.length,
        elements: checked.elements,
      },
      visualAcceptance: "not-performed",
      browserAcceptance: "not-performed",
      semanticAcceptance: "not-performed",
      scope:
        "Recompiled source and text retained; explicit host font inventory and reference raster match. Outline pixels require separate qualification. Tool file hashes are not complete native-library closure or hostile-process isolation.",
    };
    const output = await writeSourceBundle(
      plan.output,
      { id: "ethos:outlined-poster", revision: poster.source.commit },
      [
        { path: "source.svg", content: source },
        { path: "text.txt", content: text },
        { path: "outlined.svg", content: outlined },
        { path: "observation.json", content: encode(result) },
      ],
    );
    return { ...result, output };
  } finally {
    await fs.rm(scratch, { recursive: true, force: true });
  }
}
