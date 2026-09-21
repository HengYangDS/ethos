import { gzipSync, gunzipSync } from "node:zlib";
import { LIMITS, fail } from "architecture-publisher/source";

const record = (value) => value !== null && typeof value === "object" && !Array.isArray(value);

/** Lossless transport only; source identity and coverage are checked by intake. */
export function decodeBrowserReport(name, content) {
  if (!["report.json", "report.json.gz"].includes(name)) fail("browser_report_name");
  if (!Buffer.isBuffer(content) || !content.length || content.length > LIMITS.memberBytes)
    fail("browser_report_size");
  let value;
  try {
    const raw =
      name === "report.json.gz"
        ? gunzipSync(content, { maxOutputLength: LIMITS.memberBytes })
        : content;
    value = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(raw));
  } catch {
    fail("browser_report_decode");
  }
  if (!record(value)) fail("browser_report_record");
  return value;
}

/** @internal Development observer seam; not part of the installed runtime. */
export function encodeBrowserReport(report) {
  if (!record(report)) fail("browser_report_record");
  const raw = Buffer.from(JSON.stringify(report) + "\n");
  if (raw.length > LIMITS.memberBytes) fail("browser_report_size");
  const content = gzipSync(raw, { level: 6 });
  if (content.length > LIMITS.memberBytes) fail("browser_report_size");
  return { name: "report.json.gz", content };
}
