// //// Neoffice — added file (no upstream equivalent): Neoffice's app icons in place of upstream's brand marks.
import path from 'path'

import type { Plugin } from 'vite'

// //// Neoffice — Neoffice's app icons in place of upstream's brand marks. Every import of
// //// '@/assets/app-logos/<file>' (upstream's components, and any it adds later) resolves to the icon
// //// neoffice_theme serves (its apps_v2 set), or to src/assets/neoffice/ for one the theme lacks. The
// //// vendored files stay untouched, so a merge with upstream never conflicts on them. A file this table
// //// does not name fails the build: a new upstream logo is a decision to make, not a Frappe mark that
// //// slips back in (maintenance#1316).
export const NEOFFICE_APP_LOGOS: Record<string, string> = {
  'calendar.svg': '/assets/neoffice_theme/icons/apps_v2/calendar.svg',
  'drive.svg': '/assets/neoffice_theme/icons/apps_v2/drive.svg',
  'mail.svg': '/assets/neoffice_theme/icons/apps_v2/frappe_webmail.svg',
  'meet.png': '/assets/neoffice_theme/icons/apps_v2/meet.svg',
  'settings.svg': 'src/assets/neoffice/settings.svg',
  'sheets.svg': '/assets/neoffice_theme/icons/apps_v2/sheets.svg',
  'slides.svg': '/assets/neoffice_theme/icons/apps_v2/slides.svg',
  'suite.svg': '/assets/neoffice_theme/images/neoffice_icon.png',
  'writer.png': '/assets/neoffice_theme/icons/apps_v2/writer.svg',
}

export function neofficeAppLogos(root: string = __dirname): Plugin {
  const vendored = path.resolve(root, 'src/assets/app-logos') + path.sep
  const served = '\0neoffice-app-logo:'
  return {
    name: 'neoffice-app-logos',
    enforce: 'pre',
    resolveId(source, importer) {
      // the '@' alias runs first, so the id usually arrives as an absolute path
      const absolute = source.startsWith('@/')
        ? path.resolve(root, 'src', source.slice(2))
        : importer && source.startsWith('.')
          ? path.resolve(path.dirname(importer), source)
          : source
      if (!absolute.startsWith(vendored)) return null
      const file = absolute.slice(vendored.length)
      const target = NEOFFICE_APP_LOGOS[file]
      if (!target) {
        this.error(`No Neoffice icon for upstream logo "${file}": add it to NEOFFICE_APP_LOGOS in neoffice-app-logos.ts`)
      }
      return target.startsWith('/assets/') ? served + target : path.resolve(root, target)
    },
    load(id) {
      return id.startsWith(served) ? `export default ${JSON.stringify(id.slice(served.length))}` : null
    },
  }
}

