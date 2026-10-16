//// Neoffice — added file (no upstream equivalent): the Drive's storage bar (utils/storageGauge.js; maintenance#1598).
import { describe, expect, it } from 'vitest'

import { storageGauge } from './storageGauge'

const GB = 10 ** 9

describe('storageGauge', () => {
  it('shows the person’s use of a quota when there is one', () => {
    expect(storageGauge({ total_size: GB, limit: 4 * GB, disk: { total: 500 * GB, used: 120 * GB } })).toEqual({
      used: GB,
      limit: 4 * GB,
      percent: 25,
      volume: false,
    })
  })

  it('shows the volume the Drive writes to when there is no quota, not a made-up 5 GB', () => {
    expect(storageGauge({ total_size: 145.9 * 10 ** 6, limit: 0, disk: { total: 500 * GB, used: 120 * GB } })).toEqual(
      { used: 120 * GB, limit: 500 * GB, percent: 24, volume: true },
    )
  })

  it('shows the person’s use alone, with no bar, when the files are not on a disk it can say (S3)', () => {
    expect(storageGauge({ total_size: 145.9 * 10 ** 6, limit: 0, disk: null })).toEqual({
      used: 145.9 * 10 ** 6,
      limit: 0,
      percent: 0,
      volume: false,
    })
    // a server before this change sends no `disk`
    expect(storageGauge({ total_size: 12, limit: 0 }).limit).toBe(0)
    expect(storageGauge(null)).toEqual({ used: 0, limit: 0, percent: 0, volume: false })
  })

  it('never shows more than a full bar', () => {
    expect(storageGauge({ total_size: 9 * GB, limit: 4 * GB }).percent).toBe(100)
  })
})
