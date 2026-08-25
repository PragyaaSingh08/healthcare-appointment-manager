import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target:
          process.env.VITE_PROXY_TARGET ||
          'https://healthcare-appointment-manager-production-831c.up.railway.app',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
