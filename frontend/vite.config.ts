import path from 'path'

import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'
import { defineConfig } from 'vite'

// Backend Frappe site (suite.localhost) is served on port 8004 during dev.
// Mirror the per-app frappe-ui/vite proxy conventions so /api, /assets, /files,
// socket.io etc. are forwarded to the running bench.
const FRAPPE_BACKEND_PORT = 8004

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  define: {
    __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false',
  },
  // Served by Frappe at /assets/suite/frontend/ (build output lands in
  // ../suite/public/frontend -> exposed as /assets/suite/frontend).
  base: mode === 'production' ? '/assets/suite/frontend/' : '/',
  plugins: [
    frappeui({
      // frappe-ui/vite wires the dev proxy to the local bench, injects the
      // CSRF/boot data, and emits the Jinja-templated index html.
      frappeProxy: true,
      lucideIcons: true,
      jinjaBootData: true,
      buildConfig: {
        outDir: '../suite/public/frontend',
        baseUrl: '/assets/suite/frontend/',
        indexHtmlPath: '../suite/www/suite.html',
        emptyOutDir: true,
        sourcemap: true,
      },
    }),
    vue(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      'tailwind.config.js': path.resolve(__dirname, 'tailwind.config.js'),
    },
    // Keep single ProseMirror / Yjs / reka-ui / vue singletons across the 7
    // merged editors (drive/writer/sheets/mail collab) — see _resolved.json.
    dedupe: [
      'vue',
      'vue-router',
      'yjs',
      '@tiptap/pm',
      'prosemirror-state',
      'prosemirror-view',
      'reka-ui',
      '@vueuse/core',
    ],
  },
  build: {
    // outDir/baseUrl/indexHtmlPath are owned by frappeui buildConfig above.
    sourcemap: true,
    target: 'esnext',
    commonjsOptions: {
      include: [/tailwind.config.js/, /node_modules/],
    },
  },
  server: {
    port: 8085,
    allowedHosts: ['suite.localhost'],
    proxy: {
      // Fallback explicit proxy in case frappeProxy autodetection misses the
      // port; forward the Frappe API surface to the bench on :8004.
      '^/(app|api|assets|files|private|method)': {
        target: `http://suite.localhost:${FRAPPE_BACKEND_PORT}`,
        ws: true,
        changeOrigin: true,
        router: () => `http://suite.localhost:${FRAPPE_BACKEND_PORT}`,
      },
    },
    fs: {
      // Meet imports socketio_port from sites/common_site_config.json (outside
      // the frontend root); allow the bench + frappe-ui source paths.
      allow: ['..', 'node_modules', '../../..'],
    },
  },
  optimizeDeps: {
    include: [
      'frappe-ui > feather-icons',
      'frappe-ui > lowlight',
      'yjs',
      'tailwind.config.js',
    ],
    exclude: mode === 'production' ? [] : ['frappe-ui'],
  },
}))
