// //// Neoffice — added file (no upstream equivalent): dates in the reader's language.
// //// Upstream never sets a dayjs locale, so every date suite formats with dayjs reads English
// //// whatever the account's language: month and day names ("Oct", "Thu"), relative times
// //// ("2 hours ago"), localized formats ("LT" as "2:00 PM"). The page declares the account's
// //// language on <html lang> (www/suite.py). Suite loads dayjs twice, as `dayjs/esm` (the
// //// calendar, mail and slides helpers) and as `dayjs` (frappe-ui and a few components), and
// //// each copy keeps its own locale, so both are set (#1316).
import dayjsEsm from 'dayjs/esm'
import 'dayjs/esm/locale/de'
import 'dayjs/esm/locale/fr'
import 'dayjs/esm/locale/it'
import dayjs from 'dayjs'
import 'dayjs/locale/de'
import 'dayjs/locale/fr'
import 'dayjs/locale/it'

// The languages Neoffice ships besides English. Anything else keeps dayjs' English.
const SUPPORTED = ['de', 'fr', 'it']

export function setDateLocale(lang: string | null | undefined = document.documentElement.lang): string {
  const base = (lang || 'en').toLowerCase().split(/[-_]/)[0]
  const locale = SUPPORTED.includes(base) ? base : 'en'
  dayjsEsm.locale(locale)
  dayjs.locale(locale)
  return locale
}
