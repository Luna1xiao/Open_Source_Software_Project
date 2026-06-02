import path from "node:path";
import {
  backendDir,
  desktopDir,
  repoRoot,
  resolveDesktopPython,
  resolvePnpmExecutable,
  runCommand,
} from "./tooling.mjs";

async function main() {
  await buildUi();
  await buildBackendSidecar();
}

async function buildUi() {
  const pnpm = await resolvePnpmExecutable();
  await runCommand(pnpm, ["--dir", repoRoot, "--filter", "ui", "build"], {
    cwd: desktopDir,
  });
}

async function buildBackendSidecar() {
  const python = await resolveDesktopPython();
  await runCommand(python.command, [...python.args, path.join(backendDir, "scripts", "build_sidecar.py")], {
    cwd: repoRoot,
  });
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
