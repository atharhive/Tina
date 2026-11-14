/**
 * Tina — Telegraph Protocol Autonomous Verification Terminal
 */
import { spawn } from "node:child_process";
import { resolve } from "node:path";

console.log("Starting Tina Autonomous Terminal...");
const py = spawn("python3", ["core/engine.py"], {
  stdio: "inherit",
  env: process.env,
});

py.on("close", (code) => {
  process.exit(code);
});
