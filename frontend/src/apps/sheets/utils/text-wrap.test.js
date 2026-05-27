import { describe, it, expect } from 'vitest'
import { getTextWrap, isWrapText, WRAP_MODES } from './text-wrap.js'

describe('getTextWrap', () => {
  it('returns "overflow" for missing format / missing field', () => {
    expect(getTextWrap()).toBe('overflow')
    expect(getTextWrap(null)).toBe('overflow')
    expect(getTextWrap({})).toBe('overflow')
  })

  it('returns the new-style enum when set', () => {
    expect(getTextWrap({ textWrap: 'overflow' })).toBe('overflow')
    expect(getTextWrap({ textWrap: 'clip' })).toBe('clip')
    expect(getTextWrap({ textWrap: 'wrap' })).toBe('wrap')
  })

  it('falls back to legacy wrapText boolean — true → "wrap"', () => {
    expect(getTextWrap({ wrapText: true })).toBe('wrap')
  })

  it('legacy wrapText: false → "overflow" (new default, not "clip")', () => {
    // Pre-3-mode users only ever opted into wrap or didn't. There's no
    // legacy "clip" state to migrate from, so treat absence/false as the
    // new default mode.
    expect(getTextWrap({ wrapText: false })).toBe('overflow')
  })

  it('new field wins over legacy field', () => {
    expect(getTextWrap({ textWrap: 'clip', wrapText: true })).toBe('clip')
    expect(getTextWrap({ textWrap: 'overflow', wrapText: true })).toBe('overflow')
  })

  it('rejects unknown enum values and falls through to fallbacks', () => {
    expect(getTextWrap({ textWrap: 'bogus' })).toBe('overflow')
    expect(getTextWrap({ textWrap: 'bogus', wrapText: true })).toBe('wrap')
  })
})

describe('isWrapText', () => {
  it('true only for wrap mode', () => {
    expect(isWrapText({ textWrap: 'wrap' })).toBe(true)
    expect(isWrapText({ wrapText: true })).toBe(true)
    expect(isWrapText({ textWrap: 'overflow' })).toBe(false)
    expect(isWrapText({ textWrap: 'clip' })).toBe(false)
    expect(isWrapText({})).toBe(false)
  })
})

describe('WRAP_MODES', () => {
  it('exposes the three valid modes', () => {
    expect(WRAP_MODES).toEqual(['overflow', 'clip', 'wrap'])
  })
})
