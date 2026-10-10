//// Neoffice — added file (no upstream equivalent): a translation's context (maintenance#1387).
import { afterEach, describe, expect, it } from 'vitest'

import { translate } from './translation'

describe('translate', () => {
	afterEach(() => {
		window.translatedMessages = undefined
	})

	it("takes the context's own translation first, as frappe's __() does", () => {
		// The catalogue keys a context as "msgid:context": the status "Open" is "Ouvert", the verb is "Ouvrir".
		window.translatedMessages = { Open: 'Ouvert', 'Open:Action': 'Ouvrir' }
		expect(translate('Open', null, 'Action')).toBe('Ouvrir')
		expect(translate('Open')).toBe('Ouvert')
	})

	it('falls back to the message without its context, then to the message itself', () => {
		window.translatedMessages = { Close: 'Fermer' }
		expect(translate('Close', null, 'Action')).toBe('Fermer')
		expect(translate('Archive', null, 'Action')).toBe('Archive')
	})

	it('still fills the placeholders of a translation found by its context', () => {
		window.translatedMessages = { '{0} at {1}:Alert': '{0} à {1}' }
		expect(translate('{0} at {1}', ['sam. 10 oct.', '11:00'], 'Alert')).toBe('sam. 10 oct. à 11:00')
	})
})
