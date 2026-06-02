import { mkdir, mkdtemp, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import { desktopDir, runCommand } from "./tooling.mjs";

const iconPng = path.join(desktopDir, "icons", "icon.png");
const outputIcns = path.join(desktopDir, "icons", "icon.icns");

async function main() {
  if (process.platform !== "darwin") {
    return;
  }

  const tempRoot = await mkdtemp(path.join(os.tmpdir(), "mercury-iconset-"));
  const iconsetDir = path.join(tempRoot, "icon.iconset");

  try {
    await mkdir(iconsetDir, { recursive: true });
    await generateIconVariant(iconsetDir, "16x16", 16);
    await generateIconVariant(iconsetDir, "16x16@2x", 32);
    await generateIconVariant(iconsetDir, "32x32", 32);
    await generateIconVariant(iconsetDir, "32x32@2x", 64);
    await generateIconVariant(iconsetDir, "128x128", 128);
    await generateIconVariant(iconsetDir, "128x128@2x", 256);
    await generateIconVariant(iconsetDir, "256x256", 256);
    await generateIconVariant(iconsetDir, "256x256@2x", 512);
    await generateIconVariant(iconsetDir, "512x512", 512);
    await generateIconVariant(iconsetDir, "512x512@2x", 1024);
    await runCommand("iconutil", ["-c", "icns", iconsetDir, "-o", outputIcns], { cwd: desktopDir });
  } finally {
    await rm(tempRoot, { recursive: true, force: true });
  }
}

async function generateIconVariant(iconsetDir, label, size) {
  const output = path.join(iconsetDir, `icon_${label}.png`);
  await runCommand("sips", ["-z", String(size), String(size), iconPng, "--out", output], { cwd: desktopDir });
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
