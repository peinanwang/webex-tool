import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// `npm run dev` (or ../dev.sh) serves the UI with instant reload and forwards /api to the Python backend.
// BACKEND_URL picks which backend: the real listener (default :8000) or the UI sandbox (:8765).
// `npm run build` writes ui/dist/, which the Python app also serves at its own port.
const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: Number(process.env.UI_PORT ?? 5173),
    strictPort: true,
    proxy: { "/api": { target: backend, changeOrigin: true } },
  },
});
