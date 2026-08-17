import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // forwards /api/* to Flask during `npm run dev` so the browser
      // never has to worry about CORS or hardcoded hostnames
      "/api": "http://localhost:5000",
    },
  },
})
