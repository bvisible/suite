// //// Neoffice — added file (no upstream equivalent): frappe-ui's calendar in the reader's language (maintenance#1321).
import type { Plugin } from 'vite'

// //// Neoffice — frappe-ui's experimental Calendar (the grid of the Calendar app) writes English by hand: its month
// //// and weekday names are English arrays, its dates go through toLocaleDateString('en-US'), and its « Today »,
// //// « Day », « Week », « Month », « All day » and « n more » are literals. A French account read « October 2026 »
// //// above « Sun Mon Tue ». The files live in node_modules, so this plugin rewrites them as Vite loads them: the
// //// names come from Intl in the page's language (<html lang>, set by www/suite.py) and the words go through __().
// //// Every rewrite must find its text: a frappe-ui update that changes one fails the build here, instead of
// //// bringing English back in silence.
// ////
// //// The grid also started every week on Sunday, in the month as in the week (maintenance#1346): the first of the
// //// month went in the column of its getDay(), the header listed Sunday first, a timed event took the column of its
// //// getDay(). The week now starts on the site's first day of the week (System Settings, Monday in Switzerland),
// //// which www/suite.py puts on window.first_day_of_the_week, as the desk's calendars use it. Sunday where the page
// //// carries none, as upstream draws it.

type Rewrite = { find: RegExp | string; replace: string }

// Hoisted declarations: monthList and daysList are computed while the module evaluates.
export const HELPERS = `
// //// Neoffice — the reader's language for the names above (neoffice-calendar-i18n.ts).
function neoLang() {
  return (typeof document !== 'undefined' && document.documentElement.lang) || 'en-US'
}
function neoMonths(width) {
  return Array.from({ length: 12 }, (_, m) => new Date(2026, m, 1).toLocaleDateString(neoLang(), { month: width }))
}
function neoDays(width) {
  // 1 February 2026 is a Sunday: the lists start on Sunday, as getDay() counts. neoWeekOrder() turns them.
  return Array.from({ length: 7 }, (_, d) => new Date(2026, 1, 1 + d).toLocaleDateString(neoLang(), { weekday: width }))
}
// //// Neoffice — the week starts on the site's first day of the week (neoffice-calendar-i18n.ts, #1346).
function neoWeekStart() {
  const day = typeof window !== 'undefined' ? window.first_day_of_the_week : undefined
  const index = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].indexOf(day)
  return index < 0 ? 0 : index
}
function neoWeekColumn(date) {
  // the column of a date in that week, where upstream read date.getDay()
  return (date.getDay() - neoWeekStart() + 7) % 7
}
function neoWeekOrder(days) {
  // a Sunday-first list of the seven days, in the order of that week
  const start = neoWeekStart()
  return days.slice(start).concat(days.slice(0, start))
}
`

// What the other files of the calendar import from calendarUtils.ts.
const EXPORTS = `
export { neoWeekColumn, neoWeekOrder }
`

export const CALENDAR_REWRITES: Record<string, Rewrite[]> = {
  'calendarUtils.ts': [
    { find: /export const monthList = \[[^\]]*\]/, replace: "export const monthList = neoMonths('long')" },
    { find: /export const daysList = \[[^\]]*\]/, replace: "export const daysList = neoDays('short')" },
    { find: /export const daysListFull = \[[^\]]*\]/, replace: "export const daysListFull = neoDays('long')" },
    { find: "toLocaleDateString('en-US', options)", replace: 'toLocaleDateString(neoLang(), options)' },
    // the first of the month in the column of its weekday, counted from the site's first day
    { find: 'let leftPadding = firstDay.getDay()', replace: 'let leftPadding = neoWeekColumn(firstDay)' },
  ],
  'Calendar.vue': [
    { find: '<Button label="Today" ', replace: `<Button :label="__('Today')" ` },
    { find: "{ label: 'Day', value: 'Day',", replace: "{ label: __('Day'), value: 'Day'," },
    { find: "{ label: 'Week', value: 'Week',", replace: "{ label: __('Week'), value: 'Week'," },
    { find: "{ label: 'Month', value: 'Month',", replace: "{ label: __('Month'), value: 'Month'," },
  ],
  'CalendarMonthStack.vue': [{ find: "return 'All day'", replace: "return __('All day')" }],
  'CalendarDaily.vue': [
    {
      find: `:label="dayFullDayEvents.length - 4 + ' more'"`,
      replace: `:label="__('{0} more', [String(dayFullDayEvents.length - 4)])"`,
    },
    // the label of the all-day row, a bare text node
    { find: /(inline-flex items-center"\s*>)\s*All day\s*(<\/div>)/, replace: "$1{{ __('All day') }}$2" },
  ],
  'CalendarWeekly.vue': [
    { find: `:label="hiddenCount(col) + ' more'"`, replace: `:label="__('{0} more', [String(hiddenCount(col))])"` },
    // the label of the all-day row, a bare text node
    { find: /(inline-flex items-center"\s*>)\s*All day\s*(<\/div>)/, replace: "$1{{ __('All day') }}$2" },
  ],
  // the Month view's week rows, from the site's first day
  'monthStrip.ts': [
    {
      find: "import { monthList, parseDate } from './calendarUtils'",
      replace: "import { monthList, neoWeekColumn, parseDate } from './calendarUtils'",
    },
    { find: 'return addDays(date, -date.getDay())', replace: 'return addDays(date, -neoWeekColumn(date))' },
  ],
  // the column a timed event moves within, when dragged sideways
  'CalendarWeekDayEvent.vue': [
    { find: "  formattedDuration,\n} from './calendarUtils'", replace: "  formattedDuration,\n  neoWeekColumn,\n} from './calendarUtils'" },
    { find: ': new Date(props.date).getDay()', replace: ': neoWeekColumn(new Date(props.date))' },
  ],
  'CalendarMonthly.vue': [
    {
      find: "import { daysList, isWeekend, parseDate } from './calendarUtils'",
      replace: "import { daysList, isWeekend, neoWeekOrder, parseDate } from './calendarUtils'",
    },
    // the header of the month, from the site's first day
    { find: 'v-for="day in daysList"', replace: 'v-for="day in neoWeekOrder(daysList)"' },
    // the first of a month names it: « 1 oct. » in French, « Oct 1 » in English (upstream wrote « Oct 1 » for all)
    {
      find: 'return `${shortMonth(date)} 1`',
      replace:
        "return date.toLocaleDateString((typeof document !== 'undefined' && document.documentElement.lang) || 'en-US', { day: 'numeric', month: 'short' })",
    },
  ],
}

const CALENDAR_DIR = /[\\/]frappe-ui[\\/]experimental[\\/]Calendar[\\/]([^\\/]+)$/

/** Applies the rewrites of one file; reports the first text it cannot find. */
export function rewriteCalendarFile(file: string, code: string): { code: string; missing?: string } {
  const rewrites = CALENDAR_REWRITES[file]
  if (!rewrites) return { code }
  let out = code
  for (const { find, replace } of rewrites) {
    const found = typeof find === 'string' ? out.includes(find) : find.test(out)
    if (!found) return { code, missing: String(find) }
    out = out.replace(find, replace)
  }
  if (file === 'calendarUtils.ts') out += HELPERS + EXPORTS
  return { code: out }
}

export function neofficeCalendarI18n(): Plugin {
  return {
    name: 'neoffice-calendar-i18n',
    enforce: 'pre',
    transform(code, id) {
      // the SFC itself, before the Vue plugin splits it: its ?vue&type=… parts are already compiled
      if (id.includes('?')) return null
      const match = id.match(CALENDAR_DIR)
      if (!match || !CALENDAR_REWRITES[match[1]]) return null
      const { code: out, missing } = rewriteCalendarFile(match[1], code)
      if (missing) {
        this.error(
          `frappe-ui's ${match[1]} no longer contains ${missing}: update CALENDAR_REWRITES in neoffice-calendar-i18n.ts`,
        )
      }
      return { code: out, map: null }
    },
  }
}
