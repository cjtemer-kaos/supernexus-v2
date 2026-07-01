import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "./",

  resolve: {
    alias: {
      "@": "/src",
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:9000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
