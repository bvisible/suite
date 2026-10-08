/**
 * Single source of truth for the 7 suite apps.
 *
 * Both the router (one lazy route group per app, prefix preserved) and the
 * shell launcher (app switcher) read this list. A per-app port should NOT need
 * to edit this file — it only fills in src/apps/<id>/routes.ts. The id here
 * must match the directory name under src/apps/.
 *
 * Logos are the apps' own brand marks, vendored under src/assets/app-logos/ and
 * imported so Vite fingerprints them into the shared shell bundle.
 */
//// Neoffice — upstream's six per-app logo imports are gone (calendar, drive, mail,
//// meet, sheets, slides, writer): the tiles take the brand's Streamline icons served
//// by neoffice_theme (NEOFFICE_APP_ICONS), the same as the cockpit's switcher, so the
//// launcher matches the rest of Neoffice (the older animated set it used was retired on
//// 27.09). suiteLogo resolves to Neoffice's mark (neoffice-app-logos.ts). The
//// vendored files under src/assets/app-logos/ are untouched.
import suiteLogo from '@/assets/app-logos/suite.svg'
import { jmapUser, systemUser } from '@/boot/session'
import { NEOFFICE_APP_ICONS } from '@/neoffice/appIcons'

export interface SuiteApp {
  id: string
  /** Display name shown in the launcher / top-nav. */
  name: string
  /** URL prefix this app owns. */
  prefix: string
  /** Imported, build-fingerprinted brand-logo URL. */
  logo: string
  // //// Neoffice: full-page URL served OUTSIDE this SPA (launcher renders a
  // plain <a>). Used to point the Mail tile at our frappe_webmail app. ////
  external?: string
  // //// Neoffice: launcher tile creates a blank Office file (docx/xlsx/pptx)
  // in the Drive and opens it in Collabora, replacing the native editors. ////
  createsOffice?: 'docx' | 'xlsx' | 'pptx'
}

export interface SuiteAppSwitcherItem {
  name: string
  title: string
  route: string
  logo: string
  spa: boolean
}

export const SUITE_LOGO = suiteLogo

// //// Neoffice: every tile's logo is the brand's icon of the app (NEOFFICE_APP_ICONS, see the header) ////
export const SUITE_APPS: SuiteApp[] = [
  { id: 'drive', name: 'Drive', prefix: '/drive', logo: NEOFFICE_APP_ICONS.drive },
  // //// Neoffice: Slides/Writer/Sheets tiles create a Collabora-backed Office
  // file in the Drive (pptx/docx/xlsx) instead of opening the native editors.
  // The native SPAs stay reachable at their /slides /writer /sheets URLs. ////
  { id: 'slides', name: 'Slides', prefix: '/slides', logo: NEOFFICE_APP_ICONS.slides, createsOffice: 'pptx' },
  { id: 'writer', name: 'Writer', prefix: '/writer', logo: NEOFFICE_APP_ICONS.writer, createsOffice: 'docx' },
  { id: 'sheets', name: 'Sheets', prefix: '/sheets', logo: NEOFFICE_APP_ICONS.sheets, createsOffice: 'xlsx' },
  { id: 'meet', name: 'Meet', prefix: '/meet', logo: NEOFFICE_APP_ICONS.meet },
  // //// Neoffice: the Mail tile opens our frappe_webmail — the DESK page
  // /app/webmail (the maintained path; the website route /webmail stays stuck
  // on "Chargement…" because the SPA bundle is only injected in the desk).
  // The JMAP mail client stays reachable at /mail. ////
  { id: 'mail', name: 'Mail', prefix: '/mail', logo: NEOFFICE_APP_ICONS.mail, external: '/app/webmail' },
  { id: 'calendar', name: 'Calendar', prefix: '/calendar', logo: NEOFFICE_APP_ICONS.calendar },
]

export const SUITE_APP_SWITCHER_ITEMS: SuiteAppSwitcherItem[] = SUITE_APPS.map((app) => ({
  name: app.id,
  title: app.name,
  route: app.prefix,
  logo: app.logo,
  spa: true,
}))

export const DESK_APP_SWITCHER_ITEM: SuiteAppSwitcherItem = {
  name: 'frappe',
  title: 'Desk',
  route: '/app',
  logo: '/assets/frappe/images/framework.png',
  spa: false,
}

export function getAppSwitcherItems(currentApp: string): SuiteAppSwitcherItem[] {
  const items = [
    ...(systemUser.value ? [DESK_APP_SWITCHER_ITEM] : []),
    ...SUITE_APP_SWITCHER_ITEMS.filter((app) => app.name !== currentApp),
  ]
  if (!jmapUser.value) {
    return items.filter((app) => app.name !== 'mail' && app.name !== 'calendar')
  }
  return items
}
