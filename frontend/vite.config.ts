import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/agent": {
        target: "https://www.gravaity-cybernaut.top",
        changeOrigin: true,
        secure: true,
        ws: true,
      },
      "/api": {
        target: "https://www.gravaity-cybernaut.top",
        changeOrigin: true,
        secure: true,
      },
    },
  },
});


