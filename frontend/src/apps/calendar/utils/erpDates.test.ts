//// Neoffice — added file (no upstream equivalent): tests of erpDates.ts (maintenance#1428).
import { describe, expect, it } from 'vitest'

import {
	LATE_PALETTE,
	erpEventPalette,
	erpEventRoute,
	isErpCalendar,
	isErpEvent,
	swatch,
} from '@/apps/calendar/utils/erpDates'

describe('telling the dates of the ERP apart', () => {
	it('reads the flag the server sets, and nothing else', () => {
		expect(isErpCalendar({ virtual: 1 })).toBe(true)
		expect(isErpCalendar({ virtual: 0 })).toBe(false)
		expect(isErpCalendar({ id: 'erp:tasks' })).toBe(false) // an id that merely looks like one is not enough
		expect(isErpCalendar(undefined)).toBe(false)
		expect(isErpEvent({ virtual: 1, read_only: 1 })).toBe(true)
		expect(isErpEvent({})).toBe(false)
		expect(isErpEvent(null)).toBe(false)
	})
})

describe('the colour of a dot', () => {
	it('draws a palette name with the ink of the grid, since CSS has no amber or violet', () => {
		expect(swatch('amber')).toBe('var(--ink-amber-6)')
		expect(swatch('violet')).toBe('var(--ink-violet-6)')
	})

	it('leaves a real colour alone', () => {
		expect(swatch('#9BA3AF')).toBe('#9BA3AF')
		expect(swatch('rgb(1, 2, 3)')).toBe('rgb(1, 2, 3)')
	})

	it('draws nothing for nothing', () => {
		expect(swatch(undefined)).toBeUndefined()
		expect(swatch(null)).toBeUndefined()
		expect(swatch('')).toBeUndefined()
	})
})

describe('the colour of a pill', () => {
	it('is its source\'s, and pink when the date is late', () => {
		expect(erpEventPalette({ late: 0, palette: 'green' }, 'green')).toBe('green')
		expect(erpEventPalette({ late: 1, palette: 'green' }, 'green')).toBe(LATE_PALETTE)
		expect(erpEventPalette({ late: 1 })).toBe(LATE_PALETTE)
	})

	it('falls back on the event\'s own palette when the calendar says none', () => {
		expect(erpEventPalette({ palette: 'cyan' }, '')).toBe('cyan')
		expect(erpEventPalette({}, undefined)).toBeUndefined()
	})
})

describe('where a date opens its document', () => {
	it('follows a page of the desk', () => {
		expect(erpEventRoute({ route: '/app/todo/TODO-1' })).toBe('/app/todo/TODO-1')
		expect(erpEventRoute({ route: '/app/booking-session/BKS-2026-0001' })).toBe('/app/booking-session/BKS-2026-0001')
	})

	it('follows nothing else', () => {
		for (const route of [
			'',
			undefined,
			'https://evil.example/app/todo/x',
			'//evil.example/app/todo/x',
			'javascript:alert(1)',
			'/calendar',
			'/app/todo/a b',
			'app/todo/x',
		])
			expect(erpEventRoute({ route }), String(route)).toBe('')
		expect(erpEventRoute(null)).toBe('')
	})
})
