import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 9967,
    host: '0.0.0.0',
    allowedHosts: ['tre.hopto.org', 'localhost'],
    proxy: {
      '/delivery/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/delivery\/api/, '/api'),
      },
    },
  },
})
