import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev (npm run dev) API calls go to the Python server on :8000.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000' } },
})
