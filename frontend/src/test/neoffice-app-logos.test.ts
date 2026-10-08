// //// Neoffice — added file (no upstream equivalent): tests of neoffice-app-logos.ts (maintenance#1316).
import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

import { NEOFFICE_APP_LOGOS, neofficeAppLogos } from '../../neoffice-app-logos'

const root = path.resolve(__dirname, '../..')
const vendored = path.join(root, 'src/assets/app-logos')

function resolve(source: string, importer?: string) {
  const plugin = neofficeAppLogos(root)
  const errors: string[] = []
  const context = {
    error(message: string): never {
      errors.push(message)
      throw new Error(message)
    },
  }
  const hook = plugin.resolveId as (this: typeof context, source: string, importer?: string) => string | null
  let id: string | null = null
  try {
    id = hook.call(context, source, importer)
  } catch {
    // reported through errors
  }
  return { id, errors, load: plugin.load as (id: string) => string | null }
}

describe('Neoffice app logos', () => {
  it('names a Neoffice icon for every logo upstream vendors', () => {
    // A logo upstream adds to src/assets/app-logos must be given ours here, or the build fails on it.
    const files = fs.readdirSync(vendored).filter((f) => !f.startsWith('.'))
    expect(files.length).toBeGreaterThan(0)
    expect(files.filter((f) => !(f in NEOFFICE_APP_LOGOS))).toEqual([])
  })

  it('turns an upstream logo import into the icon neoffice_theme serves', () => {
    const { id, load } = resolve(path.join(vendored, 'meet.png'))
    expect(id).toBeTruthy()
    expect(load(id as string)).toBe('export default "/assets/neoffice_theme/icons/apps_v2/meet.svg"')
  })

  it('reads the "@/" form and a relative import the same way', () => {
    const viaAlias = resolve('@/assets/app-logos/calendar.svg')
    const relative = resolve('../../../assets/app-logos/calendar.svg', path.join(root, 'src/apps/calendar/pages/X.vue'))
    expect(viaAlias.load(viaAlias.id as string)).toContain('apps_v2/calendar.svg')
    expect(relative.load(relative.id as string)).toContain('apps_v2/calendar.svg')
  })

  it('points a logo the theme lacks to our own file in src/assets/neoffice', () => {
    const { id } = resolve(path.join(vendored, 'settings.svg'))
    expect(id).toBe(path.join(root, 'src/assets/neoffice/settings.svg'))
    expect(fs.readFileSync(id as string, 'utf8')).toContain('neo-settings-bg')
  })

  it('fails on a logo it does not know, instead of letting a Frappe mark through', () => {
    const { id, errors } = resolve(path.join(vendored, 'brand-new-app.svg'))
    expect(id).toBeNull()
    expect(errors[0]).toContain('No Neoffice icon for upstream logo "brand-new-app.svg"')
  })

  it('leaves every other import alone', () => {
    expect(resolve('@/apps/meet/pages/Home.vue').id).toBeNull()
    expect(resolve('vue').id).toBeNull()
  })
})
