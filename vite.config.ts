import path from 'path';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { visualizer } from 'rollup-plugin-visualizer';
import { defineConfig, type Plugin } from 'vite';

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    process.env.ANALYZE === 'true' &&
      visualizer({
        filename: 'dist/stats.html',
        open: true,
        gzipSize: true,
        brotliSize: true,
      }),
  ].filter(Boolean) as Plugin[],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  base: './', // Ensures static deployment compatibility (e.g. GitHub Pages)
  server: {
    port: 5173,
    host: true,
    watch: {
      ignored: [
        '**/*.md',
        '**/.git/**',
        '**/docs/**',
        '**/backend_docs/**',
        '**/backend/**',
        '**/.github/**',
        '**/evaluation/**',
        '**/scripts/**',
        '**/sugestions by frontend/**',
      ],
    },
  },
});

