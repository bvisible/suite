// //// Neoffice — added file (no upstream equivalent): lists, in src/neoffice/i18nRegistry.ts, every message the build
// //// asks the catalogue for in the apps that upstream wrote without __() (neoffice-i18n-core.mjs, maintenance#1592).
// ////
// //// The sources of those apps no longer name the messages (the Vite plugin wraps them as it loads the files), and
// //// the extractor of the translation catalogues reads sources: this file is what it finds. Run it after a change
// //// to those apps (a merge from upstream above all) and commit the result with the new translations:
// ////
// ////   node scripts/gen-i18n-registry.mjs            # writes src/neoffice/i18nRegistry.ts
// ////   node scripts/gen-i18n-registry.mjs --check    # exits 1 when the file is stale (what the test does too)
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { collectMessages } from '../neoffice-i18n-core.mjs'
import { registrySource } from './gen-i18n-registry-source.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const out = path.join(root, 'src/neoffice/i18nRegistry.ts')

const { messages, left } = collectMessages(root)
const source = registrySource(messages)

if (process.argv.includes('--check')) {
  const current = fs.existsSync(out) ? fs.readFileSync(out, 'utf8') : ''
  if (current !== source) {
    console.error('src/neoffice/i18nRegistry.ts is stale: run node scripts/gen-i18n-registry.mjs')
    process.exit(1)
  }
  console.log(`registry is current (${messages.length} messages)`)
} else {
  fs.mkdirSync(path.dirname(out), { recursive: true })
  fs.writeFileSync(out, source)
  console.log(`${messages.length} messages -> ${path.relative(root, out)}`)
  if (left.length) {
    console.log(`${left.length} fragments left alone (next to an element inside one sentence):`)
    for (const l of left) console.log(`  ${l.file}:${l.line}  ${JSON.stringify(l.text.slice(0, 90))}`)
  }
}
