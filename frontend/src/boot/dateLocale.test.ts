// //// Neoffice — added file (no upstream equivalent): tests of boot/dateLocale.ts (#1316).
import { afterEach, describe, expect, it } from 'vitest'
import dayjsEsm from 'dayjs/esm'
import dayjs from 'dayjs'
import localizedFormat from 'dayjs/esm/plugin/localizedFormat'

import { setDateLocale } from './dateLocale'

dayjsEsm.extend(localizedFormat)

const OCTOBER_8 = '2026-10-08T14:30:00'

describe('setDateLocale', () => {
  afterEach(() => {
    setDateLocale('en')
  })

  it('makes both copies of dayjs speak the language of the page', () => {
    document.documentElement.lang = 'fr'
    expect(setDateLocale()).toBe('fr')
    expect(dayjsEsm(OCTOBER_8).format('MMM')).toBe('oct.')
    expect(dayjs(OCTOBER_8).format('dddd')).toBe('jeudi')
  })

  it('gives French the 24-hour clock in localized formats', () => {
    setDateLocale('fr')
    expect(dayjsEsm(OCTOBER_8).format('LT')).toBe('14:30')
  })

  it('reads a regional tag by its language', () => {
    expect(setDateLocale('de-CH')).toBe('de')
    expect(dayjsEsm(OCTOBER_8).format('MMMM')).toBe('Oktober')
  })

  it('keeps English for a language Neoffice does not ship', () => {
    expect(setDateLocale('xx')).toBe('en')
    expect(dayjsEsm(OCTOBER_8).format('MMM')).toBe('Oct')
    expect(setDateLocale(null)).toBe('en')
  })
})
