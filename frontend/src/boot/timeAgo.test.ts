// //// Neoffice — added file (no upstream equivalent): tests of boot/timeAgo.ts.
import { afterEach, describe, expect, it } from 'vitest'

import { timeAgo } from './timeAgo'

const MINUTE = 60_000
const DAY = 24 * 60 * MINUTE

describe('timeAgo', () => {
  afterEach(() => {
    document.documentElement.lang = ''
  })

  it('says a relative time in the language of the page', () => {
    document.documentElement.lang = 'fr'
    expect(timeAgo(Date.now() - 2 * MINUTE).value).toBe('il y a 2 minutes')
    expect(timeAgo(Date.now() - DAY).value).toBe('hier')
    expect(timeAgo(new Date()).value).toBe('maintenant')
  })

  it('reads a regional tag, and the other languages Neoffice ships', () => {
    document.documentElement.lang = 'fr-CH'
    expect(timeAgo(Date.now() - 3 * DAY).value).toBe('il y a 3 jours')
    document.documentElement.lang = 'de'
    expect(timeAgo(Date.now() - 2 * MINUTE).value).toBe('vor 2 Minuten')
    document.documentElement.lang = 'en'
    expect(timeAgo(Date.now() - 2 * MINUTE).value).toBe('2 minutes ago')
  })

  it('takes a date as the server writes it', () => {
    document.documentElement.lang = 'fr'
    // A day and a few minutes ago, to the minute, as `2026-10-12 17:45:00`
    const at = new Date(Date.now() - DAY - 5 * MINUTE)
    const two = (n: number) => String(n).padStart(2, '0')
    const written = `${at.getFullYear()}-${two(at.getMonth() + 1)}-${two(at.getDate())} ${two(at.getHours())}:${two(at.getMinutes())}:00`
    expect(timeAgo(written).value).toBe('hier')
  })
})
