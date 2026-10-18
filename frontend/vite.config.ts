import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // The built Sphinx docs (see docs/), served by the Flask backend -- so "Help" links
      // work against the dev server too, not just the production build.
      '/docs': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
