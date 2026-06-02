import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const desktopDir = path.resolve(__dirname, "..");
export const repoRoot = path.resolve(desktopDir, "..", "..");
export const backendDir = path.join(repoRoot, "backend");
export const isWindows = process.platform === "win32";

export async function resolvePnpmExecutable() {
  if (!isWindows) {
    return "pnpm";
  }

  const candidates = await getWindowsPnpmCandidates();
  for (const candidate of candidates) {
    try {
      await runCommand(candidate, ["--version"], { cwd: desktopDir, quiet: true });
      return candidate;
    } catch {
      // Try the next candidate.
    }
  }

  throw new Error("Unable to find a working pnpm executable for the desktop scripts.");
}

export async function resolveDesktopPython() {
  const candidates = isWindows
    ? [
        { command: "py", args: ["-3.11"] },
        { command: "py", args: ["-3.12"] },
        { command: "python3.11", args: [] },
        { command: "python", args: [] },
      ]
    : [
        { command: "python3.11", args: [] },
        { command: "python3", args: [] },
        { command: "python", args: [] },
      ];

  for (const candidate of candidates) {
    try {
      const version = await captureCommand(candidate.command, [...candidate.args, "--version"]);
      if (isCompatiblePython(version)) {
        return candidate;
      }
    } catch {
      // Try the next candidate.
    }
  }

  throw new Error("Desktop builds require Python 3.11 or newer to package the backend sidecar.");
}

export function runCommand(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: options.cwd,
      env: { ...process.env, ...(options.env ?? {}) },
      stdio: options.quiet ? "pipe" : "inherit",
      shell: isWindows,
    });

    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) {
        resolve();
        return;
      }

      reject(new Error(`${command} ${args.join(" ")} exited with code ${code ?? "unknown"}`));
    });
  });
}

export function captureCommand(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    let stdout = "";
    let stderr = "";
    const child = spawn(command, args, {
      cwd: options.cwd,
      env: { ...process.env, ...(options.env ?? {}) },
      shell: isWindows,
    });

    child.stdout?.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr?.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) {
        resolve(stdout);
        return;
      }

      reject(new Error(stderr || `${command} ${args.join(" ")} exited with code ${code ?? "unknown"}`));
    });
  });
}

function isCompatiblePython(versionOutput) {
  const match = versionOutput.match(/Python\s+(\d+)\.(\d+)/i);
  if (!match) {
    return false;
  }

  const major = Number(match[1]);
  const minor = Number(match[2]);
  return major > 3 || (major === 3 && minor >= 11);
}

async function getWindowsPnpmCandidates() {
  const output = await captureCommand("where.exe", ["pnpm.cmd"]);
  const candidates = output
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  const preferred = candidates.filter((candidate) => !candidate.includes("\\Program Files\\nodejs\\"));
  return [...preferred, ...candidates.filter((candidate) => candidate.includes("\\Program Files\\nodejs\\"))];
}
