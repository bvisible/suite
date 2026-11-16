import { afterEach, describe, expect, it } from 'vitest'

import { jmapUser, systemUser } from '@/boot/session'
//// Neoffice — OFFERED_APPS and SUITE_APPS for the tests of #1311 below.
import { OFFERED_APPS, SUITE_APPS, getAppSwitcherItems, getPhoneAppSwitcherItems } from './registry'

const names = (currentApp: string) => getPhoneAppSwitcherItems(currentApp).map((app) => app.name)

describe('getPhoneAppSwitcherItems', () => {
	afterEach(() => {
		jmapUser.value = false
		systemUser.value = false
	})

	it('leads with the current app, then only the other apps with a phone layout', () => {
		jmapUser.value = true
		expect(names('mail')).toEqual(['mail', 'calendar'])
		expect(names('calendar')).toEqual(['calendar', 'mail'])
	})

	it('leaves Desk out even for a system user, since it has no phone layout', () => {
		jmapUser.value = true
		systemUser.value = true
		expect(names('mail')).toEqual(['mail', 'calendar'])
	})

	it('offers no other app the desktop menu would not', () => {
		jmapUser.value = false
		expect(names('mail')).toEqual(['mail'])
	})

	it('can include the current app for the command palette', () => {
		jmapUser.value = true
		expect(getAppSwitcherItems('mail', true).map((app) => app.name)).toContain('mail')
	})
})

//// Neoffice — added tests (#1311): Writer, Slides and Sheets are not offered; their routes stay.
describe('the apps we offer', () => {
	afterEach(() => {
		jmapUser.value = false
		systemUser.value = false
	})

	it('leaves Writer, Slides and Sheets out of the launcher and the switcher', () => {
		jmapUser.value = true
		systemUser.value = true
		const offered = OFFERED_APPS.map((app) => app.id)
		const switcher = getAppSwitcherItems('drive', true).map((app) => app.name)
		for (const id of ['writer', 'slides', 'sheets']) {
			expect(offered).not.toContain(id)
			expect(switcher).not.toContain(id)
		}
		expect(offered).toEqual(expect.arrayContaining(['drive', 'meet', 'mail', 'calendar']))
		expect(switcher).toEqual(expect.arrayContaining(['frappe', 'drive', 'meet', 'mail', 'calendar']))
	})

	it('keeps their code and routes: the registry the router reads still has them', () => {
		const all = SUITE_APPS.map((app) => app.id)
		expect(all).toEqual(expect.arrayContaining(['writer', 'slides', 'sheets']))
	})
})
