import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    middlewareMode: false,
    proxy: {
      '/api': {
        target: 'https://localhost:443',
        changeOrigin: true,
        secure: false, // Aceita certificados auto-assinados
        rewrite: (path) => path, // Não reescreve, mantém /api
        ws: false,
        logLevel: 'debug'
      },
      '/auth': {
        target: 'https://localhost:443',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path,
        ws: false
      },
      '/webhook': {
        target: 'https://localhost:443',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path,
        ws: false
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'esbuild'
  }
})
