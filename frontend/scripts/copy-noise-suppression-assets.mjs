/**
 * Copy the prebundled DTLN AudioWorklet processor out of node_modules into
 * suite/public so Vite never fingerprints/emits ~40MB of wasm + models on
 * every production build.
 *
 * Frappe serves: /assets/suite/noise-suppression/audio-worklet-processor.js
 * Vite dev serves the same directory via vite.config middleware at
 * /noise-suppression/audio-worklet-processor.js
 *
 * The processor ships LiteRT wasm + DTLN models base64-inlined (package
 * README); only this single file is required for the worklet path.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const appRoot = path.resolve(frontendRoot, '..')

//// Neoffice — look in frontend/node_modules as well as the app root.
//// @workadventure/noise-suppression is declared in frontend/package.json, so a
//// package manager run from frontend/ (pnpm, as our CI does) installs it under
//// frontend/node_modules. Upstream only looks at the app root, which happens to
//// work on a checkout that also ran `yarn install` there — and fails everywhere
//// else. It broke our GitHub build on the first run (31.08.2026); it would break
//// any clean clone the same way.
const RELATIVE_SOURCE =
  'node_modules/@workadventure/noise-suppression/dist/assets/audio-worklet-processor.js'

const candidates = [
  path.join(frontendRoot, RELATIVE_SOURCE),
  path.join(appRoot, RELATIVE_SOURCE),
]
const source = candidates.find((candidate) => fs.existsSync(candidate)) ?? candidates[0]

const dest = path.join(
  appRoot,
  'suite/public/noise-suppression/audio-worklet-processor.js',
)

if (!fs.existsSync(source)) {
  console.error(
    `[copy-noise-suppression-assets] Source missing: ${source}\n` +
      `Looked in:\n  ${candidates.join('\n  ')}\n` +
      'Install @workadventure/noise-suppression first (pnpm install in frontend/).',
  )
  process.exit(1)
}

fs.mkdirSync(path.dirname(dest), { recursive: true })
fs.copyFileSync(source, dest)
const mb = (fs.statSync(dest).size / (1024 * 1024)).toFixed(1)
console.log(`[copy-noise-suppression-assets] ${dest} (${mb} MB)`)
