import fs from 'fs'
import path from 'path'

import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'
import { defineConfig } from 'vite'

const benchRoot = path.resolve(__dirname, '../../..')
const commonSiteConfig = JSON.parse(
  fs.readFileSync(path.join(benchRoot, 'sites/common_site_config.json'), 'utf-8'),
)
const defaultSite = commonSiteConfig.default_site || 'localhost'
const webserverPort = commonSiteConfig.webserver_port || 8000
const frappeBackendUrl = `http://${defaultSite}:${webserverPort}`

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  define: {
    __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false',
    __SOCKETIO_PORT__: JSON.stringify(commonSiteConfig.socketio_port || 9000),
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
    allowedHosts: [defaultSite, 'suite.localhost'],
    proxy: {
      // Fallback explicit proxy in case frappeProxy autodetection misses the
      // port; forward the Frappe API surface to the bench webserver port.
      '^/(app|api|assets|files|private|method|website_script\\.js)': {
        target: frappeBackendUrl,
        ws: true,
        changeOrigin: true,
        router: () => frappeBackendUrl,
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
