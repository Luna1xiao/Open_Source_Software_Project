import { spawn, spawnSync } from "node:child_process";
import { access } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../../..");
const backendDir = path.join(repoRoot, "backend");
const outputFile = path.join(repoRoot, "packages/shared-types/src/generated.ts");
const port = process.env.MERCURY_PORT ?? "8000";
const openapiUrl = `http://127.0.0.1:${port}/openapi.json`;
const cliPath = path.join(
  repoRoot,
  "node_modules/.pnpm/openapi-typescript@7.13.0_typescript@5.9.3/node_modules/openapi-typescript/bin/cli.js"
);

let backendProcess;

try {
  await access(cliPath);

  if (!(await isBackendAvailable())) {
    backendProcess = startBackend();
    await waitForBackend();
  }

  await runNodeProcess(process.execPath, [cliPath, openapiUrl, "-o", outputFile], repoRoot);
  console.log(`Wrote ${outputFile}`);
} finally {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill();
  }
}

async function isBackendAvailable() {
  try {
    const response = await fetch(openapiUrl);
    return response.ok;
  } catch {
    return false;
  }
}

function startBackend() {
  const commands = [
    { command: "uv", args: ["run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", port] },
    { command: "py", args: ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", port] },
    { command: "python", args: ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", port] }
  ];

  for (const option of commands) {
    if (!commandExists(option.command)) {
      continue;
    }

    return spawn(option.command, option.args, {
      cwd: backendDir,
      env: { ...process.env, MERCURY_PORT: port },
      stdio: "inherit"
    });
  }

  throw new Error("Unable to start backend for OpenAPI generation.");
}

async function waitForBackend() {
  for (let index = 0; index < 30; index += 1) {
    if (await isBackendAvailable()) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Backend did not become ready at ${openapiUrl}`);
}

async function runNodeProcess(command, args, cwd) {
  await new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd,
      stdio: "inherit",
      env: process.env
    });

    child.on("exit", (code) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(new Error(`${command} exited with code ${code ?? -1}`));
    });

    child.on("error", reject);
  });
}

function commandExists(command) {
  const locator = process.platform === "win32" ? "where" : "which";
  const result = spawnSync(locator, [command], { stdio: "ignore" });
  return result.status === 0;
}
