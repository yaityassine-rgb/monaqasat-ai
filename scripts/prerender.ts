/**
 * Pre-rendering script for Monaqasat AI
 *
 * Visits each public route with Puppeteer and saves the fully-rendered HTML.
 * This ensures crawlers and social media preview bots see real content
 * instead of an empty <div id="root"></div>.
 *
 * Usage:
 *   npx tsx scripts/prerender.ts
 *
 * Run after `npm run build` (the postbuild script does this automatically).
 */

import puppeteer from "puppeteer";
import { createServer } from "vite";
import { writeFileSync, mkdirSync } from "fs";
import { resolve, dirname } from "path";

const LANGS = ["en", "ar", "fr"] as const;

const PUBLIC_ROUTES = [
  "", // home
  "/about",
  "/pricing",
  "/contact",
  "/terms",
  "/privacy",
  "/refund",
];

const DIST_DIR = resolve(import.meta.dirname, "..", "dist");

async function prerender() {
  console.log("[prerender] Starting Vite preview server...");

  // Start a Vite preview server on the built output
  const server = await createServer({
    root: resolve(import.meta.dirname, ".."),
    server: { port: 4199, strictPort: true },
    preview: { port: 4199 },
  });
  await server.listen();
  const serverUrl = "http://localhost:4199";

  console.log(`[prerender] Server running at ${serverUrl}`);

  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const routes: string[] = [];
  for (const lang of LANGS) {
    for (const route of PUBLIC_ROUTES) {
      routes.push(`/${lang}${route}`);
    }
  }

  console.log(`[prerender] Pre-rendering ${routes.length} routes...`);

  for (const route of routes) {
    const page = await browser.newPage();
    const url = `${serverUrl}${route}`;

    try {
      await page.goto(url, { waitUntil: "networkidle0", timeout: 15000 });

      // Wait for React to render
      await page.waitForSelector("[data-reactroot], #root > *", {
        timeout: 10000,
      }).catch(() => {
        // If no specific selector, just wait a moment
      });

      // Small delay for any dynamic content
      await new Promise((r) => setTimeout(r, 500));

      const html = await page.content();

      // Determine output path
      const cleanRoute = route === "/" ? "/index" : route;
      const outPath = resolve(DIST_DIR, `.${cleanRoute}`, "index.html");

      mkdirSync(dirname(outPath), { recursive: true });
      writeFileSync(outPath, html, "utf-8");

      console.log(`  [ok] ${route} → ${outPath.replace(DIST_DIR, "dist")}`);
    } catch (err) {
      console.error(`  [err] ${route}: ${err}`);
    } finally {
      await page.close();
    }
  }

  await browser.close();
  await server.close();

  console.log(`[prerender] Done! ${routes.length} pages pre-rendered.`);
}

prerender().catch((err) => {
  console.error("[prerender] Fatal error:", err);
  process.exit(1);
});
