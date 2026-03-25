import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    open: true,
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) {
            return;
          }

          if (id.includes(`${'node_modules'}/d3`) || id.includes(`${'node_modules'}\\d3`)) {
            return 'd3';
          }

          if (
            id.includes(`${'node_modules'}/vue`) ||
            id.includes(`${'node_modules'}\\vue`) ||
            id.includes(`${'node_modules'}/vue-router`) ||
            id.includes(`${'node_modules'}\\vue-router`) ||
            id.includes(`${'node_modules'}/@vue`) ||
            id.includes(`${'node_modules'}\\@vue`)
          ) {
            return 'framework';
          }

          return 'vendor';
        }
      }
    }
  }
})
