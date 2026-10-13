// //// Neoffice — added file (no upstream equivalent): tests of utils/pageTitle.ts (canvas « Neodesk », board 11).
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import dayjs from 'dayjs/esm'
import localizedFormat from 'dayjs/esm/plugin/localizedFormat'

import { setDateLocale } from '@/boot/dateLocale'
import { isoWeek, pageTitle } from './pageTitle'

dayjs.extend(localizedFormat)

const week = (startDate: string, endDate: string) => ({ view: 'Week', startDate, endDate })

describe('pageTitle', () => {
	beforeEach(() => {
		setDateLocale('fr')
	})
	afterEach(() => {
		setDateLocale('en')
	})

	it('names a week by its month, the week beside it', () => {
		expect(pageTitle(week('2026-10-12', '2026-10-18'), '', dayjs, 'Semaine')).toEqual({
			title: 'Octobre 2026',
			sub: 'Semaine 42',
		})
	})

	it('names both months of a week across two, and both years of a week across two', () => {
		expect(pageTitle(week('2026-09-28', '2026-10-04'), '', dayjs, 'Semaine').title).toBe('Septembre – octobre 2026')
		expect(pageTitle(week('2026-12-28', '2027-01-03'), '', dayjs, 'Semaine')).toEqual({
			title: 'Décembre 2026 – janvier 2027',
			sub: 'Semaine 53',
		})
	})

	it('writes the day in full in the day view', () => {
		const day = { view: 'Day', startDate: '2026-10-13', endDate: '2026-10-13' }
		expect(pageTitle(day, '', dayjs, 'Semaine')).toEqual({ title: 'Mardi 13 octobre 2026', sub: '' })
	})

	it("keeps frappe-ui's month label in the month view, with its capital", () => {
		const month = { view: 'Month', startDate: '2026-09-28', endDate: '2026-11-08' }
		expect(pageTitle(month, 'octobre 2026', dayjs, 'Semaine')).toEqual({ title: 'Octobre 2026', sub: '' })
		expect(pageTitle(null, 'octobre 2026', dayjs, 'Semaine').title).toBe('Octobre 2026')
	})
})

describe('isoWeek', () => {
	it('counts the week that holds the first Thursday as week 1', () => {
		expect(isoWeek(new Date(2026, 9, 13))).toBe(42)
		expect(isoWeek(new Date(2021, 0, 3))).toBe(53)
		expect(isoWeek(new Date(2021, 0, 4))).toBe(1)
		expect(isoWeek(new Date(2026, 0, 1))).toBe(1)
	})
})
