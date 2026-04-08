import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { runsPlugin } from "./vite-plugin-runs";

export default defineConfig({
  plugins: [react(), tailwindcss(), runsPlugin()],
});
