#!/usr/bin/env node
// Mirror the version-controlled interactive manual (the source of truth) into the
// VitePress public/ directory so it ships at /interactive/.
//
// docs/interactive/            <- edit here (the launcher cantus-manual.html opens this)
// docs/site/public/interactive/ <- generated copy (VitePress copies public/ verbatim to dist)
//
// Run explicitly with `npm run sync:interactive`. It also runs automatically as
// predocs:build / predocs:dev, so a forgotten manual copy can never make the
// deployed site stale.

import { rmSync, mkdirSync, cpSync, existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const src = resolve(root, "docs/interactive");
const dst = resolve(root, "docs/site/public/interactive");

if (!existsSync(src)) {
  console.error("[sync_interactive] source missing: " + src);
  process.exit(1);
}

// Clean mirror so files removed from the source also disappear downstream.
rmSync(dst, { recursive: true, force: true });
mkdirSync(dirname(dst), { recursive: true });
cpSync(src, dst, { recursive: true });

console.log("[sync_interactive] mirrored docs/interactive/ -> docs/site/public/interactive/");
