/// <reference types="vitest/config" />
// One self-contained HTML file: every script and style is inlined by
// vite-plugin-singlefile so the packaged app makes no external requests.
import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

export default defineConfig({
  plugins: [viteSingleFile()],
  build: {
    outDir: "dist",
    // Deterministic output: no hashed names survive single-file inlining,
    // and sourcemaps are omitted from the shipped artifact. The default
    // minifier applies (Vite 8 dropped bundled esbuild).
    sourcemap: false,
  },
  test: {
    environment: "node",
    include: ["test/**/*.test.ts"],
  },
});
