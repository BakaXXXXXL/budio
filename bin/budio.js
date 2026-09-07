#!/usr/bin/env node

"use strict";

const { spawn, execSync } = require("child_process");
const path = require("path");
const fs = require("fs");

const PYTHON_DIR = path.join(__dirname, "..", "python");
const PYTHON_SCRIPT = path.join(PYTHON_DIR, "bilibili_extractor.py");
const REQUIREMENTS = path.join(PYTHON_DIR, "requirements.txt");

function findPython() {
  if (process.env.BILIAUDIO_PYTHON) {
    return process.env.BILIAUDIO_PYTHON;
  }

  const candidates =
    process.platform === "win32"
      ? ["python", "python3", "py"]
      : ["python3", "python"];

  return candidates;
}

function installDeps(python) {
  if (!fs.existsSync(REQUIREMENTS)) {
    return true;
  }

  console.log("[budio] Installing Python dependencies...");
  const commands = [
    `${python} -m pip install --user --break-system-packages -r "${REQUIREMENTS}"`,
    `${python} -m pip install --user -r "${REQUIREMENTS}"`,
  ];

  for (const cmd of commands) {
    try {
      execSync(cmd, { stdio: "inherit" });
      console.log("[budio] Dependencies installed successfully.\n");
      return true;
    } catch (err) {
      // Try next command
    }
  }

  console.warn("[budio] WARNING: Could not install dependencies automatically.");
  console.warn(`  Please run manually: ${python} -m pip install -r "${REQUIREMENTS}"\n`);
  return false;
}

function run() {
  if (!fs.existsSync(PYTHON_SCRIPT)) {
    console.error("Error: Python script not found at " + PYTHON_SCRIPT);
    process.exit(1);
  }

  const candidates = findPython();

  function tryPython(index) {
    if (typeof candidates === "string") {
      installDeps(candidates);
      return spawn(candidates, [PYTHON_SCRIPT, ...process.argv.slice(2)], {
        stdio: "inherit",
        env: process.env,
      });
    }

    if (index >= candidates.length) {
      console.error(
        "Error: Python 3 is required but was not found.\n" +
          "Please install Python 3.10+ and ensure it is on your PATH.\n" +
          "You can also set the BILIAUDIO_PYTHON env var to the path of your Python executable."
      );
      process.exit(1);
    }

    const cmd = candidates[index];
    try {
      execSync(`${cmd} --version`, { stdio: "ignore" });
      installDeps(cmd);
      const child = spawn(cmd, [PYTHON_SCRIPT, ...process.argv.slice(2)], {
        stdio: "inherit",
        env: process.env,
      });
      child.on("exit", (code) => {
        process.exit(code ?? 1);
      });
    } catch {
      tryPython(index + 1);
    }
  }

  tryPython(0);
}

run();
