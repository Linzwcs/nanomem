import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/manager/assets/",
  build: {
    outDir: "../src/nanomem/manager/assets",
    emptyOutDir: false,
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        entryFileNames: "app.js",
        chunkFileNames: "app-[hash].js",
        assetFileNames: (assetInfo) =>
          assetInfo.name?.endsWith(".css") ? "styles.css" : "[name]-[hash][extname]",
      },
    },
  },
  server: {
    proxy: {
      "/manager/api": "http://127.0.0.1:8765",
    },
  },
});
