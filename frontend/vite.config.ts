import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import vueDevTools from 'vite-plugin-vue-devtools'

// Same paths as frontend/nginx.conf: the browser sees one origin, so no CORS in dev or prod.
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:18000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), vueDevTools(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': apiTarget,
      '/health': apiTarget,
      '/ws': { target: apiTarget, ws: true },
    },
  },
})
