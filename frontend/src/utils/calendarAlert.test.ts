//// Neoffice — added file (no upstream equivalent): the button of a calendar alert's toast (maintenance#1387).
import { describe, expect, it, vi } from 'vitest'

const { message } = vi.hoisted(() => ({ message: vi.fn() }))
vi.mock('frappe-ui', () => ({ toast: { message } }))
vi.mock('@/router', () => ({ default: { push: vi.fn() } }))

import { showCalendarAlert } from './calendarAlert'

describe('showCalendarAlert', () => {
	it('names its button with the verb, not with the status that shares its English word', () => {
		// "Open" alone is a status in the catalogues ("Ouvert"); the verb is "Open" in the Action context
		// ("Ouvrir"), as Drive's own button asks for it.
		const asked: unknown[][] = []
		const translate = globalThis.__
		globalThis.__ = ((...args: unknown[]) => {
			asked.push(args)
			return String(args[0])
		}) as typeof globalThis.__
		try {
			showCalendarAlert({ title: 'Inventaire', body: 'jeu. 5 nov. à 08:00', path: '/calendar' })
		} finally {
			globalThis.__ = translate
		}
		expect(message).toHaveBeenCalledOnce()
		expect(asked).toContainEqual(['Open', null, 'Action'])
	})
})
