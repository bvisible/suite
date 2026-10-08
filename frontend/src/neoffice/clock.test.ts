// //// Neoffice — added file (no upstream equivalent): tests of src/neoffice/clock.ts (maintenance#1321).
import dayjs from 'dayjs/esm'
import 'dayjs/esm/locale/fr'
import 'dayjs/esm/locale/de'
import localizedFormat from 'dayjs/esm/plugin/localizedFormat'
import { afterEach, describe, expect, it } from 'vitest'

import { clockTime, usesMeridiem } from './clock'

dayjs.extend(localizedFormat)
const at = (time: string) => dayjs(`2026-10-08T${time}:00`)

describe('clock times in the reader\'s language', () => {
  afterEach(() => {
    dayjs.locale('en')
  })

  it("keep upstream's 12-hour patterns in English", () => {
    expect(usesMeridiem(at('15:00'))).toBe(true)
    expect(clockTime(at('15:00'))).toBe('3:00 pm')
    expect(clockTime(at('15:00'), 'h:mm A')).toBe('3:00 PM')
  })

  it('read the 24-hour clock in French and German', () => {
    for (const locale of ['fr', 'de']) {
      dayjs.locale(locale)
      expect(usesMeridiem(at('15:00')), locale).toBe(false)
      expect(clockTime(at('15:00')), locale).toBe('15:00')
      expect(clockTime(at('09:05'), 'h:mm A'), locale).toBe('09:05')
    }
  })

  it('take a 24-hour pattern of their own where the 12-hour one carries more', () => {
    dayjs.locale('fr')
    expect(clockTime(at('15:00'), 'D MMM, h:mm a', 'D MMM, LT')).toBe('8 oct., 15:00')
  })
})
