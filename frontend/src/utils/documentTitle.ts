import calendarLogo from '@/assets/app-logos/calendar.svg'
import driveLogo from '@/assets/app-logos/drive.svg'
import mailLogo from '@/assets/app-logos/mail.svg'
import meetLogo from '@/assets/app-logos/meet.png'
import sheetsLogo from '@/assets/app-logos/sheets.svg'
import slidesLogo from '@/assets/app-logos/slides.svg'
import writerLogo from '@/assets/app-logos/writer.png'

const APP_LOGOS: Record<string, string> = {
  Calendar: calendarLogo,
  Drive: driveLogo,
  Mail: mailLogo,
  Meet: meetLogo,
  Sheets: sheetsLogo,
  Slides: slidesLogo,
  Writer: writerLogo,
}

export function appDocumentTitle(pageTitle: string | undefined, appName: string) {
  const title = pageTitle?.trim()
  //// Neoffice — the app's name in the person's language, as the launcher and the sidebars show it (#1316):
  //// "Calendrier | Neoffice", not "Calendar" in a French account's tab. The icon keeps the English key.
  const name = __(appName)
  if (!title || title === appName || title === name || title === `Frappe ${appName}`) return name
  if (title.endsWith(` | ${appName}`) || title.endsWith(` | ${name}`)) return title
  return `${title} | ${name}`
}

export function appPageMeta(pageTitle: string | undefined, appName: string) {
  return {
    title: appDocumentTitle(pageTitle, appName),
    icon: APP_LOGOS[appName],
  }
}
