#!/usr/bin/env node

"use strict";

const { execSync } = require("child_process");
const path = require("path");
const fs = require("fs");

const PYTHON_DIR = path.join(__dirname, "..", "python");
const REQUIREMENTS = path.join(PYTHON_DIR, "requirements.txt");
const VENV_DIR = path.join(PYTHON_DIR, ".venv");

function findPython3() {
  if (process.env.BILIAUDIO_PYTHON) return process.env.BILIAUDIO_PYTHON;
  const candidates =
    process.platform === "win32"
      ? ["python", "python3", "py"]
      : ["python3", "python"];

  for (const cmd of candidates) {
    try {
      execSync(`${cmd} --version`, { stdio: "ignore" });
      return cmd;
    } catch {
      // try next
    }
  }
  return null;
}

function main() {
  const python = findPython3();
  if (!python) {
    console.warn(
      "\n[biliaudio] WARNING: Python 3 not found.\n" +
        "The tool requires Python 3.10+ to run.\n" +
        "Please install Python and ensure it is on your PATH.\n"
    );
    process.exit(0);
  }

  console.log(`[biliaudio] Using Python: ${python}`);

  if (!fs.existsSync(REQUIREMENTS)) {
    console.log("[biliaudio] No requirements.txt found, skipping.");
    return;
  }

  console.log("[biliaudio] Installing Python dependencies...");

  // Try different pip install strategies
  const commands = [
    `${python} -m pip install --user --break-system-packages -r "${REQUIREMENTS}"`,
    `${python} -m pip install --user -r "${REQUIREMENTS}"`,
  ];

  let success = false;
  for (const cmd of commands) {
    try {
      execSync(cmd, { stdio: "inherit" });
      success = true;
      break;
    } catch (err) {
      // Try next command
    }
  }

  if (success) {
    console.log("[biliaudio] Python dependencies installed successfully.");
  } else {
    console.warn(
      "\n[biliaudio] WARNING: Could not install Python dependencies.\n" +
        `  Please run manually:\n` +
        `  ${python} -m pip install -r "${REQUIREMENTS}"\n`
    );
    process.exit(0);
  }
}

main();
