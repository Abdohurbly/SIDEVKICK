import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000, // You can change the port if needed
    proxy: {
      // Proxy API requests to the Python backend during development
      '/api': {
        target: 'http://localhost:8000', // Your FastAPI backend URL
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '') // Remove /api prefix if your FastAPI doesn't expect it
      }
    }
  }
})
