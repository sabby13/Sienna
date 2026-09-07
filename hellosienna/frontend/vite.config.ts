import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Served at "/" by FastAPI; assets under "/assets". base "/" is correct.
export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist", assetsDir: "assets" },
  test: { environment: "jsdom", globals: true },
});
