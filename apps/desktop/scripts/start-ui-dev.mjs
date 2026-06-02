import { desktopDir, repoRoot, resolvePnpmExecutable, runCommand } from "./tooling.mjs";

async function main() {
  const pnpm = await resolvePnpmExecutable();
  await runCommand(pnpm, ["--dir", repoRoot, "--filter", "ui", "dev"], {
    cwd: desktopDir,
  });
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
