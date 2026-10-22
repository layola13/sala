import fs from "node:fs";
import { WASI } from "node:wasi";
import { performance } from "node:perf_hooks";

const file = process.argv[2];
if (!file) {
  console.error("usage: node wasm_runner.mjs <module.wasm>");
  process.exit(2);
}

const bytes = fs.readFileSync(file);
const wasi = new WASI({
  version: "preview1",
  args: ["sa", file],
  env: {},
  returnOnExit: true,
});

const t0 = performance.now();
const { instance } = await WebAssembly.instantiate(bytes, wasi.getImportObject());
const t1 = performance.now();
const code = wasi.start(instance);
const t2 = performance.now();

console.error(
  `METRIC ${JSON.stringify({
    init_ms: t1 - t0,
    run_ms: t2 - t1,
    total_ms: t2 - t0,
    exit_code: code,
    bytes: bytes.length,
  })}`
);
process.exitCode = code;
