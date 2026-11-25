import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Build trafia do backend/static, żeby FastAPI serwował jedną aplikację
// (wymaganie „uruchomienie jednym poleceniem”).
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../backend/static',
    emptyOutDir: true,
    sourcemap: false,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
