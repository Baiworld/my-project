import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:5000",
      "/auth": "http://localhost:5000",
      "/socket.io": {
        target: "http://localhost:5000",
        ws: true,
      },
    },
  },
});
