/** Run a bounded read batch through the selected package's official CLI program. */
import { readFileSync, writeSync } from "node:fs";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const [entry, timeout, expectedVersion] = process.argv.slice(2);
const duration = Number(timeout) * 1000;
if (!Number.isFinite(duration) || duration <= 0) {
  throw new Error("openspec_batch_deadline_invalid");
}
const deadline = performance.now() + duration;
const pause = new Int32Array(new SharedArrayBuffer(4));
const { program } = await import(
  pathToFileURL(createRequire(pathToFileURL(entry)).resolve("@fission-ai/openspec")).href
);
if (program.version() !== expectedVersion) {
  writeSync(2, "openspec_effective_version_mismatch\n");
  process.exit(1);
}
const commands = JSON.parse(readFileSync(0, "utf8"));
let active;

function finish(code) {
  if (!active) return;
  const packet = Buffer.from(JSON.stringify({ ...active, exit_code: code }) + "\n");
  active = undefined;
  for (let offset = 0; offset < packet.length;) {
    try {
      offset += writeSync(1, packet, offset);
    } catch (error) {
      if (!["EAGAIN", "EINTR"].includes(error.code)) throw error;
      const remaining = deadline - performance.now();
      if (remaining <= 0) {
        throw new Error("openspec_batch_write_timeout", { cause: error });
      }
      Atomics.wait(pause, 0, 0, Math.min(1, remaining));
    }
  }
}

function capture(name) {
  return (chunk, encoding, callback) => {
    if (active) {
      active[name] += Buffer.isBuffer(chunk)
        ? chunk.toString(typeof encoding === "string" ? encoding : "utf8")
        : String(chunk);
    }
    if (typeof encoding === "function") encoding();
    else if (typeof callback === "function") callback();
    return true;
  };
}

process.stdout.write = capture("stdout");
process.stderr.write = capture("stderr");
process.once("exit", finish);
for (const [index, args] of commands.entries()) {
  active = { index, args, stdout: "", stderr: "" };
  process.argv = [process.execPath, entry, ...args];
  process.exitCode = 0;
  await program.parseAsync(args, { from: "user" });
  finish(process.exitCode ?? 0);
}
process.exitCode = 0;
