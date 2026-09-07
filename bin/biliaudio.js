#!/usr/bin/env node

"use strict";

const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const PYTHON_DIR = path.join(__dirname, "..", "python");
const PYTHON_SCRIPT = path.join(PYTHON_DIR, "bilibili_extractor.py");

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

function run() {
  if (!fs.existsSync(PYTHON_SCRIPT)) {
    console.error("Error: Python script not found at " + PYTHON_SCRIPT);
    process.exit(1);
  }

  const candidates = findPython();
  const args = [PYTHON_SCRIPT, ...process.argv.slice(2)];

  function tryPython(index) {
    if (typeof candidates === "string") {
      return spawn(candidates, args, {
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
    const child = spawn(cmd, args, {
      stdio: "inherit",
      env: process.env,
    });

    child.on("error", () => {
      tryPython(index + 1);
    });

    child.on("exit", (code) => {
      process.exit(code ?? 1);
    });
  }

  tryPython(0);
}

run();
