import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { pathToFileURL } from "node:url";

const input = JSON.parse(readFileSync(0, "utf8"));
const prettierRequire = createRequire(process.argv[2]);
const lintRequire = createRequire(process.argv[3]);
const prettier = (await import(pathToFileURL(prettierRequire.resolve("prettier")))).default;
const { main } = await import(pathToFileURL(lintRequire.resolve("markdownlint-cli2")));
const compatibility = JSON.parse(
  readFileSync(lintRequire.resolve("markdownlint/style/prettier"), "utf8"),
);
delete compatibility.comment;
const selected = new Set(input.format_paths);
const formatted = Object.fromEntries(
  await Promise.all(
    Object.entries(input.sources).map(async ([path, source]) => [
      path,
      selected.has(path)
        ? await prettier.format(source, { ...input.settings, filepath: path })
        : source,
    ]),
  ),
);
let findings = [];
let lintExit = 0;
const diagnostics = [];
let reported = false;
if (input.lint) {
  const policy = {
    ...input.policy,
    config: { ...input.policy.config, ...compatibility },
    overrides: (input.policy.overrides ?? []).map((override) => ({
      ...override,
      config: { ...override.config, ...compatibility },
    })),
    globs: [],
    noInlineConfig: true,
    noBanner: true,
    noProgress: true,
    outputFormatters: [
      [
        (result) => {
          reported = true;
          findings = result.results;
        },
      ],
    ],
  };
  lintExit = await main({
    directory: input.directory,
    argv: [],
    noGlobs: true,
    noImport: true,
    nonFileContents: Object.fromEntries(
      Object.entries(input.sources)
        .filter(([name]) => name.endsWith(".md"))
        .map(([name, source]) => [path.resolve(input.directory, name), source]),
    ),
    optionsDefault: policy,
    logError: (message) => diagnostics.push(message),
  });
}
process.stdout.write(
  JSON.stringify({
    formatted,
    findings,
    lint_exit: lintExit,
    lint_reported: reported,
    diagnostics,
  }),
);
