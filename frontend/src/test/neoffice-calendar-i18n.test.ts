// //// Neoffice — added file (no upstream equivalent): tests of neoffice-calendar-i18n.ts (maintenance#1321, #1346).
import fs from 'node:fs'
import path from 'node:path'
import { transformWithOxc } from 'vite'
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest'

import { CALENDAR_REWRITES, HELPERS, neofficeCalendarI18n, rewriteCalendarFile } from '../../neoffice-calendar-i18n'

const calendarDir = path.resolve(__dirname, '../../node_modules/frappe-ui/experimental/Calendar')

/** frappe-ui's own file, as the build serves it: rewritten, then stripped of its types. */
async function served(file: string): Promise<string> {
  const { code, missing } = rewriteCalendarFile(file, fs.readFileSync(path.join(calendarDir, file), 'utf8'))
  if (missing) throw new Error(`${file}: ${missing}`)
  return (await transformWithOxc(code, file, { lang: 'ts' })).code.replace(
    /from (['"])\.\/(calendarUtils|eventSpan)\1/g,
    "from './$2.mjs'",
  )
}

const iso = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

const names = (lang: string) => {
  document.documentElement.lang = lang
  return new Function(`${HELPERS}; return { months: neoMonths('long'), days: neoDays('short'), full: neoDays('long') }`)()
}

describe("frappe-ui's calendar in the reader's language", () => {
  afterEach(() => {
    document.documentElement.lang = ''
  })

  it('finds every text it rewrites in the frappe-ui this build installs', () => {
    // A frappe-ui update that changes one of them must fail here, not bring English back.
    for (const file of Object.keys(CALENDAR_REWRITES)) {
      const { code, missing } = rewriteCalendarFile(file, fs.readFileSync(path.join(calendarDir, file), 'utf8'))
      expect(missing, file).toBeUndefined()
      expect(code, file).not.toMatch(/toLocaleDateString\('en-US'|label="Today"|label: 'Day'|return 'All day'|\+ ' more'/)
      expect(code, file).not.toMatch(/>\s*All day\s*<|\$\{shortMonth\(date\)\} 1/)
    }
  })

  it('names the months and weekdays in French for a French account, from Sunday', () => {
    const { months, days, full } = names('fr')
    expect(months[9]).toBe('octobre')
    expect(days).toEqual(['dim.', 'lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.'])
    expect(full[1]).toBe('lundi')
  })

  it('keeps English where the page declares no language', () => {
    const { months, days } = names('')
    expect(months[9]).toBe('October')
    expect(days[0]).toBe('Sun')
  })

  it('puts the days of the header in the order of the week', () => {
    const order = (start?: string) => {
      ;(window as unknown as Record<string, unknown>).first_day_of_the_week = start
      return new Function(`${HELPERS}; return neoWeekOrder(['dim.', 'lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.'])`)()
    }
    expect(order('Monday')).toEqual(['lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.'])
    expect(order(undefined)).toEqual(['dim.', 'lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.'])
    delete (window as unknown as Record<string, unknown>).first_day_of_the_week
  })

  it("leaves the Vue plugin's compiled parts of a file alone, and fails a file whose text moved", () => {
    const plugin = neofficeCalendarI18n()
    const transform = plugin.transform as (this: { error(m: string): never }, code: string, id: string) => unknown
    const context = {
      error(message: string): never {
        throw new Error(message)
      },
    }
    const id = path.join(calendarDir, 'Calendar.vue')
    expect(transform.call(context, 'compiled', `${id}?vue&type=script&setup=true&lang.ts`)).toBeNull()
    expect(() => transform.call(context, '<template>moved</template>', id)).toThrow(/no longer contains/)
  })
})

// The week starts on the site's first day of the week (System Settings, carried by the page's boot as
// window.first_day_of_the_week): Monday in Switzerland. frappe-ui's grid assumed Sunday (#1346).
describe("frappe-ui's calendar starts the week on the site's first day", () => {
  // Inside the project, where the test runner loads modules from (not the system's temporary folder).
  const cache = path.resolve(__dirname, '../../node_modules/.cache')
  fs.mkdirSync(cache, { recursive: true })
  const dir = fs.mkdtempSync(path.join(cache, 'neo-calendar-'))
  let utils: Record<string, (...args: never[]) => unknown>
  let strip: Record<string, (...args: never[]) => unknown>

  const startOn = (day?: string) => {
    ;(window as unknown as Record<string, unknown>).first_day_of_the_week = day
  }

  beforeAll(async () => {
    fs.writeFileSync(path.join(dir, 'calendarUtils.mjs'), await served('calendarUtils.ts'))
    fs.writeFileSync(path.join(dir, 'monthStrip.mjs'), await served('monthStrip.ts'))
    // monthStrip's week helpers never call these.
    fs.writeFileSync(path.join(dir, 'eventSpan.mjs'), 'export const eventDayCount = () => 1\nexport const eventDays = () => ({})\n')
    utils = await import(/* @vite-ignore */ path.join(dir, 'calendarUtils.mjs'))
    strip = await import(/* @vite-ignore */ path.join(dir, 'monthStrip.mjs'))
  })

  afterEach(() => startOn(undefined))
  afterAll(() => fs.rmSync(dir, { recursive: true, force: true }))

  const grid = (month: number, year: number) => (utils.getCalendarDates as (m: number, y: number) => Date[])(month, year)

  it('the grid of October 2026 opens on Monday 28 September, and every row on a Monday', () => {
    startOn('Monday')
    const dates = grid(9, 2026)
    expect(iso(dates[0]!)).toBe('2026-09-28')
    expect(dates.filter((_, i) => i % 7 === 0).map((d) => d.getDay())).toEqual(Array(dates.length / 7).fill(1))
    expect(dates.map(iso)).toContain('2026-10-31')
  })

  it('a month that begins on a Monday has no padding, one that begins on a Sunday has six days of it', () => {
    startOn('Monday')
    expect(iso(grid(5, 2026)[0]!)).toBe('2026-06-01')
    const february = grid(1, 2026)
    expect(iso(february[0]!)).toBe('2026-01-26')
    expect(iso(february[february.length - 1]!)).toBe('2026-03-01')
  })

  it('keeps Sunday where the site names no first day, as upstream draws it', () => {
    expect(iso(grid(9, 2026)[0]!)).toBe('2026-09-27')
  })

  it("the Month strip's weeks start on that day too", () => {
    startOn('Monday')
    const weeks = (strip.stripWeeks as (m: number, y: number) => Date[][])(9, 2026)
    expect(iso(weeks[0]![0]!)).toBe('2026-09-28')
    expect(weeks.map((week) => week[0]!.getDay())).toEqual(Array(weeks.length).fill(1))
    expect(iso((strip.weekStart as (d: Date) => Date)(new Date(2026, 9, 11)))).toBe('2026-10-05')
  })

  it("an event's column in the week counts from that day", () => {
    startOn('Monday')
    const column = utils.neoWeekColumn as (d: Date) => number
    expect(column(new Date(2026, 9, 5))).toBe(0)
    expect(column(new Date(2026, 9, 11))).toBe(6)
    startOn(undefined)
    expect(column(new Date(2026, 9, 5))).toBe(1)
  })
})
