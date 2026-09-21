import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";

const sha = (bytes) => createHash("sha256").update(bytes).digest("hex");
const family = "ETHOS JetBrains Mono";
const escape = (s) => s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");

function fontFaceCss(supply) {
  return supply.fonts
    .map(
      (f) =>
        `@font-face{font-family:'${family}';font-style:normal;font-weight:${f.weight};font-display:block;src:url(data:font/ttf;base64,${f.bytes.toString("base64")}) format('truetype');}`,
    )
    .join("\n");
}

/** Before native validation only. Preserve the existing layout/controller code. */
export async function applyNativeFonts(toolRoot, supply, expected) {
  const files = {
    template: path.join(toolRoot, "assets/template.html"),
    renderer: path.join(toolRoot, "renderers/architecture/render-architecture.mjs"),
  };
  const before = {
    template: await fs.readFile(files.template, "utf8"),
    renderer: await fs.readFile(files.renderer, "utf8"),
  };
  for (const key of Object.keys(files))
    if (sha(before[key]) !== expected[key]) throw Error("Font adapter digest mismatch: " + key);
  let template = before.template,
    renderer = before.renderer;
  const block = /  <!-- Async font load:[\s\S]*?<\/noscript>\n/;
  if ((template.match(block) ?? []).length !== 1) throw Error("Pinned font import seam mismatch");
  const css = fontFaceCss(supply);
  template = template.replace(
    block,
    `  <style id="ethos-font-supply">${css}</style>\n  <style>body{font-kerning:none;font-variant-ligatures:none}</style>\n`,
  );
  const local =
    /        \/\/ Prepend a local\(\)-only @font-face block[\s\S]*?        \}\)\.join\('\\n'\);/;
  if ((template.match(local) ?? []).length !== 1) throw Error("Pinned export font seam mismatch");
  template = template.replace(
    local,
    "        // Reuse the exact embedded font bytes, not installed or network fonts.\n        var fontFallback = document.getElementById('ethos-font-supply').textContent;",
  );
  const names = template.split("'JetBrains Mono'").length - 1;
  // Body, the two SVG exports, share-card measurement and share-card paint.
  if (names !== 5) throw Error("Pinned viewer/export font-family seam mismatch: " + names);
  template = template.replaceAll("'JetBrains Mono'", `'${family}'`);
  if (template.split("</body>").length !== 2) throw Error("Font license seam mismatch");
  template = template.replace(
    "</body>",
    `<details class="no-print" style="margin:24px auto;max-width:1100px;font:12px/1.5 system-ui"><summary>Font license</summary><pre style="white-space:pre-wrap">${escape(supply.license.bytes.toString())}</pre></details>\n</body>`,
  );
  const svg = '<svg viewBox="0 0 ${viewBox[0]} ${viewBox[1]}"';
  if (renderer.split(svg).length !== 2) throw Error("Pinned font SVG seam mismatch");
  renderer = renderer.replace(
    svg,
    `<svg data-ethos-font-lock="${supply.lockSha256}" style="font-family:'${family}';font-kerning:none;font-variant-ligatures:none" viewBox="0 0 \${viewBox[0]} \${viewBox[1]}"`,
  );
  await fs.writeFile(files.template, template);
  await fs.writeFile(files.renderer, renderer);
  return {
    schema: "ethos.native-font-binding/v1",
    lockSha256: supply.lockSha256,
    fonts: supply.fonts.map(({ weight, sha256, postscriptName }) => ({
      weight,
      sha256,
      postscriptName,
    })),
    patchedFiles: Object.keys(files).map((k) => ({
      path: path.relative(toolRoot, files[k]),
      before: sha(before[k]),
      after: sha(k === "template" ? template : renderer),
    })),
    scope:
      "Same unmodified embedded fonts for viewer and export; no system install or new layout owner.",
    browserAcceptance: "UNVERIFIED",
  };
}
