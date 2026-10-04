import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(process.argv[2]);
const { ESLint } = require("eslint");
const { configs } = require("@eslint/js");
const globals = require("globals");
const entries = JSON.parse(readFileSync(0, "utf8"));
const reports = [];
const engines = new Map();
for (const { path, source, sourceType } of entries) {
  if (!engines.has(sourceType))
    engines.set(
      sourceType,
      new ESLint({
        overrideConfigFile: true,
        ignore: false,
        allowInlineConfig: false,
        overrideConfig: [
          {
            files: ["**/*"],
            languageOptions: {
              ecmaVersion: "latest",
              sourceType,
              globals: sourceType === "commonjs" ? globals.node : globals.nodeBuiltin,
            },
            rules: configs.recommended.rules,
          },
        ],
      }),
    );
  reports.push(...(await engines.get(sourceType).lintText(source, { filePath: path })));
}
process.stdout.write(JSON.stringify(reports) + "\n");
process.exitCode = reports.some(({ errorCount, warningCount }) => errorCount || warningCount)
  ? 1
  : 0;
