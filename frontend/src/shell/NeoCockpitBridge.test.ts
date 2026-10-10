//// Neoffice — added file (no upstream equivalent): the cockpit's place on a phone (maintenance#1387).
import { describe, expect, it } from 'vitest'

import source from './NeoCockpitBridge.vue?raw'

describe('NeoCockpitBridge on a phone', () => {
	it('turns the row it is mounted in into a column, so the page sits under its bar', () => {
		// Every page mounts the cockpit beside its content, in a flex row (the calendar, its no-account page, Meet's
		// home, the /suite launcher). Below md the cockpit is a full-width bar: in a row it left the page 0 to 32 px.
		// jsdom lays nothing out, so the rule itself is what is checked; the screens were checked in Chrome and WebKit.
		expect(source).toMatch(
			/@media \(max-width: 767\.98px\) \{\s*\.flex:has\(> \.neocockpit-host\) \{\s*flex-direction: column;/,
		)
	})
})
