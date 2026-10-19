import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  // Relative base so the same build works at a user/org page root, a project
  // sub-path (e.g. /acgn-problem/) and a custom domain.
  base: './',
  plugins: [vue()],
  build: {
    outDir: 'dist',
    assetsInlineLimit: 4096,
  },
})
