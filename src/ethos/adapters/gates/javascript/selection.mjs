import { createRequire } from "node:module";
import { resolve, relative, isAbsolute } from "node:path";
import { readFileSync } from "node:fs";

const [c8, ...arguments_] = process.argv.slice(2);
const require = createRequire(c8);
const { buildYargs } = require("../lib/parse-args.js");
const makeReport = require("../lib/report.js");
const argv = buildYargs().parse(["report", ...arguments_]);
const report = makeReport({
  include: argv.include,
  exclude: argv.exclude,
  extension: argv.extension,
  excludeNodeModules: argv.excludeNodeModules,
  allowExternal: argv.allowExternal,
  src: argv.src,
});
const paths = JSON.parse(readFileSync(0, "utf8"));
const roots = report.src.map((path) => resolve(path));
process.stdout.write(
  JSON.stringify({
    config: argv.config ?? null,
    all: argv.all,
    selected_paths: paths.filter((path) => {
      const full = resolve(path);
      return (
        report.exclude.shouldInstrument(full) &&
        (!argv.all ||
          roots.some((root) => {
            const child = relative(root, full);
            return (
              child !== "" &&
              child !== ".." &&
              !child.startsWith("../") &&
              !child.startsWith("..\\") &&
              !isAbsolute(child)
            );
          }))
      );
    }),
  }),
);
