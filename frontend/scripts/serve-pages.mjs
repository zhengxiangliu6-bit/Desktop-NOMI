// Test fixture only: serve dist under the Pages prefix, without SPA fallback.
// This server is never uploaded or deployed; GitHub Pages serves dist itself.
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../dist/", import.meta.url));
const prefix = "/Desktop-NOMI/";
const types = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
};

createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(
      new URL(request.url, "http://localhost").pathname,
    );
    if (pathname === prefix.slice(0, -1)) {
      response.writeHead(301, { Location: prefix }).end();
      return;
    }
    if (!pathname.startsWith(prefix)) {
      response.writeHead(404).end("Not found");
      return;
    }
    const path = resolve(root, pathname.slice(prefix.length) || "index.html");
    if (!path.startsWith(root.endsWith(sep) ? root : root + sep)) {
      response.writeHead(404).end("Not found");
      return;
    }
    const body = await readFile(path);
    response
      .writeHead(200, {
        "Content-Type": types[extname(path)] ?? "application/octet-stream",
        "Cache-Control": "no-store",
      })
      .end(body);
  } catch {
    response.writeHead(404).end("Not found");
  }
}).listen(4180, "127.0.0.1", () => {
  console.log(`Pages test fixture: http://127.0.0.1:4180${prefix}`);
});
