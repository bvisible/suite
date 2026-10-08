// //// Neoffice — added file (no upstream equivalent): Drive's dates in the account's language (maintenance#1321).
import { afterEach, describe, expect, it } from 'vitest'

import { formatDate } from './format'

// ICU writes a narrow no-break space before AM/PM; the assertions read it as a space.
const read = (value: string) => value.replace(/ /g, ' ')

describe('formatDate', () => {
  afterEach(() => {
    document.documentElement.lang = ''
  })

  it('writes the day before the month, on the 24-hour clock, for a French account', () => {
    document.documentElement.lang = 'fr'
    expect(read(formatDate('2026-10-08T14:30:00'))).toBe('08/10/26, 14:30')
  })

  it('keeps the US form where the page declares no language', () => {
    expect(read(formatDate('2026-10-08T14:30:00'))).toBe('10/08/26, 02:30 PM')
  })
})
