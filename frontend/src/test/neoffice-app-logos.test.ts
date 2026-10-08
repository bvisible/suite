// //// Neoffice — added file (no upstream equivalent): tests of neoffice-app-logos.ts and of the brand's app icons
// //// Suite draws (maintenance#1316).
import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

import { NEOFFICE_APP_LOGOS, neofficeAppLogos } from '../../neoffice-app-logos'
import { NEOFFICE_APP_ICONS } from '../neoffice/appIcons'

const root = path.resolve(__dirname, '../..')
const vendored = path.join(root, 'src/assets/app-logos')
const STREAMLINE = '/assets/neoffice_theme/icons/streamline/'

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
    expect(load(id as string)).toBe(`export default "${STREAMLINE}video-camera.svg"`)
  })

  it('reads the "@/" form and a relative import the same way', () => {
    const viaAlias = resolve('@/assets/app-logos/calendar.svg')
    const relative = resolve('../../../assets/app-logos/calendar.svg', path.join(root, 'src/apps/calendar/pages/X.vue'))
    expect(viaAlias.load(viaAlias.id as string)).toContain(`${STREAMLINE}calendar.svg`)
    expect(relative.load(relative.id as string)).toContain(`${STREAMLINE}calendar.svg`)
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

describe("The brand's app icons", () => {
  it("are the theme's Streamline icons, the cockpit's own, and never a file of this repository", () => {
    // Streamline's licence: the files stay in neoffice_theme (private); Suite only names their address.
    const { suite, ...apps } = NEOFFICE_APP_ICONS
    expect(suite).toBe('/assets/neoffice_theme/images/neoffice_icon.png')
    for (const [app, url] of Object.entries(apps)) expect(url, app).toMatch(/^\/assets\/neoffice_theme\/icons\/streamline\/[a-z-]+\.svg$/)
    for (const url of Object.values(NEOFFICE_APP_LOGOS)) expect(Object.values(NEOFFICE_APP_ICONS)).toContain(url)
    expect(fs.existsSync(path.join(root, 'src/assets/neoffice'))).toBe(false)
  })

  it('match the names the theme gives them (neoffice_app_icons)', () => {
    expect(NEOFFICE_APP_ICONS).toMatchObject({
      drive: `${STREAMLINE}cloud-folder.svg`,
      calendar: `${STREAMLINE}calendar.svg`,
      meet: `${STREAMLINE}video-camera.svg`,
      mail: `${STREAMLINE}envelope.svg`,
      sheets: `${STREAMLINE}table.svg`,
      slides: `${STREAMLINE}monitor.svg`,
      writer: `${STREAMLINE}document.svg`,
      settings: `${STREAMLINE}gear.svg`,
    })
  })

  it('draw the launcher tiles and the Meet logo', () => {
    const registry = fs.readFileSync(path.join(root, 'src/apps/registry.ts'), 'utf8')
    expect(registry).not.toMatch(/apps_v2/)
    for (const app of ['drive', 'slides', 'writer', 'sheets', 'meet', 'mail', 'calendar'])
      expect(registry).toContain(`logo: NEOFFICE_APP_ICONS.${app}`)
    const meetLogo = fs.readFileSync(path.join(root, 'src/apps/meet/icons/FrappeMeetingLogo.vue'), 'utf8')
    expect(meetLogo).toContain('NEOFFICE_APP_ICONS.meet')
    expect(meetLogo).not.toMatch(/apps_v2/)
  })

  it("label the launcher's tiles in the reader's language, as the cockpit does (Calendrier, Messagerie)", () => {
    const launcher = fs.readFileSync(path.join(root, 'src/shell/LauncherView.vue'), 'utf8')
    expect(launcher).toMatch(/:label="creating === app\.id \? __\('Creating…'\) : __\(app\.name\)"/)
  })

  it('turn white in the dark theme, the clay staying clay', () => {
    const css = fs.readFileSync(path.join(root, 'src/index.css'), 'utf8')
    expect(css).toMatch(/\[data-theme='dark'\] img\[src\*='\/icons\/streamline\/'\][^{]*\{\s*filter: invert\(1\) hue-rotate\(180deg\);/)
  })
})
