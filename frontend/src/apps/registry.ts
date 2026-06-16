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
import calendarLogo from '@/assets/app-logos/calendar.svg'
import driveLogo from '@/assets/app-logos/drive.svg'
import mailLogo from '@/assets/app-logos/mail.svg'
import meetLogo from '@/assets/app-logos/meet.png'
import sheetsLogo from '@/assets/app-logos/sheets.svg'
import slidesLogo from '@/assets/app-logos/slides.svg'
import writerLogo from '@/assets/app-logos/writer.png'

export interface SuiteApp {
  id: string
  /** Display name shown in the launcher / top-nav. */
  name: string
  /** URL prefix this app owns; preserved from the original standalone app. */
  prefix: string
  /** Short blurb for the launcher tile. */
  description: string
  /** lucide icon name — fallback chrome (e.g. top-nav) when a logo isn't shown. */
  icon: string
  /** Imported, build-fingerprinted brand-logo URL. */
  logo: string
}

export const SUITE_APPS: SuiteApp[] = [
  { id: 'drive', name: 'Drive', prefix: '/drive', description: 'Files & folders', icon: 'HardDrive', logo: driveLogo },
  { id: 'slides', name: 'Slides', prefix: '/slides', description: 'Presentations', icon: 'Presentation', logo: slidesLogo },
  { id: 'writer', name: 'Writer', prefix: '/writer', description: 'Documents', icon: 'FileText', logo: writerLogo },
  { id: 'sheets', name: 'Sheets', prefix: '/sheets', description: 'Spreadsheets', icon: 'Table', logo: sheetsLogo },
  { id: 'meet', name: 'Meet', prefix: '/meet', description: 'Video meetings', icon: 'Video', logo: meetLogo },
  { id: 'mail', name: 'Mail', prefix: '/mail', description: 'Email', icon: 'Mail', logo: mailLogo },
  { id: 'calendar', name: 'Calendar', prefix: '/calendar', description: 'Schedule', icon: 'Calendar', logo: calendarLogo },
]
