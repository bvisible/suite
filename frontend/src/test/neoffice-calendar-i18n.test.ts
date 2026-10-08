// //// Neoffice — added file (no upstream equivalent): tests of neoffice-calendar-i18n.ts (maintenance#1321).
import fs from 'node:fs'
import path from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'

import { CALENDAR_REWRITES, HELPERS, neofficeCalendarI18n, rewriteCalendarFile } from '../../neoffice-calendar-i18n'

const calendarDir = path.resolve(__dirname, '../../node_modules/frappe-ui/experimental/Calendar')

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
