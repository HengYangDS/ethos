/** Run native document APIs once over literal input and conjoined policy snapshots. */
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
let formatted = input.sources;
let formatPolicyConflict = false;
for (const [index, settings] of input.settings.entries()) {
  const rendered = Object.fromEntries(
    await Promise.all(
      Object.entries(formatted).map(async ([name, source]) => [
        name,
        selected.has(name)
          ? await prettier.format(source, { ...settings, filepath: name })
          : source,
      ]),
    ),
  );
  if (index) {
    formatPolicyConflict ||= Object.keys(formatted).some(
      (name) => rendered[name] !== formatted[name],
    );
  } else {
    formatted = rendered;
  }
}
const findings = [];
let lintExit = 0;
const diagnostics = [];
let reported = input.lint;
if (input.lint) {
  for (const declared of input.policies) {
    let completed = false;
    const policy = {
      ...declared,
      config: { ...declared.config, ...compatibility },
      overrides: (declared.overrides ?? []).map((override) => ({
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
            completed = true;
            findings.push(...result.results);
          },
        ],
      ],
    };
    lintExit = Math.max(
      lintExit,
      await main({
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
      }),
    );
    reported &&= completed;
  }
}
process.stdout.write(
  JSON.stringify({
    formatted,
    format_policy_conflict: formatPolicyConflict,
    findings,
    lint_exit: lintExit,
    lint_reported: reported,
    diagnostics,
  }),
);
