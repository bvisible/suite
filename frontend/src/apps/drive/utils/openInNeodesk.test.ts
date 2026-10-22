//// Neoffice — added file (no upstream equivalent): tests of utils/openInNeodesk.js, « Ouvrir dans Neodesk ».
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
	HINT_HIDDEN_KEY,
	NEODESK_DOWNLOAD_URL,
	NOTHING_OPENED_AFTER_MS,
	editorInstalledFor,
	hideHint,
	hintHidden,
	isDesktopBrowser,
	neodeskLink,
	opensInNeodesk,
	tryNeodesk,
} from './openInNeodesk'

const site = { protocol: 'https:', hostname: 'osiris.neoffice.me', port: '' }

describe('the address handed to Neodesk', () => {
	it('names this site and the file, and nothing else', () => {
		expect(neodeskLink(site, 'ab12cd34ef')).toBe('neodesk://drive/osiris.neoffice.me/ab12cd34ef')
		expect(neodeskLink({ ...site, hostname: 'Osiris.Neoffice.ME' }, 'a-b_9')).toBe(
			'neodesk://drive/osiris.neoffice.me/a-b_9',
		)
	})

	it('is none where Neodesk could not take it', () => {
		expect(neodeskLink({ ...site, protocol: 'http:' }, 'ab12')).toBeNull()
		expect(neodeskLink({ ...site, port: '8000' }, 'ab12')).toBeNull()
		expect(neodeskLink({ ...site, hostname: 'localhost' }, 'ab12')).toBeNull()
		expect(neodeskLink(site, '../ab12')).toBeNull()
		expect(neodeskLink(site, 'ab 12')).toBeNull()
		expect(neodeskLink(site, 'x'.repeat(141))).toBeNull()
		expect(neodeskLink(site, '')).toBeNull()
		expect(neodeskLink(null, 'ab12')).toBeNull()
	})
})

describe('the files it is offered for', () => {
	it('is the four types Neodesk opens where they are', () => {
		for (const name of ['Devis.docx', 'Ventes.XLSX', 'Plan.pptx', 'Scan.pdf']) {
			expect(opensInNeodesk({ file_name: name, is_folder: 0 })).toBe(true)
		}
	})

	it('is not a folder, a link, a hosted document, an old format or a text file', () => {
		// A .txt opens in no editor of the Drive: the WordCraft editor would write it back as a .docx, a copy.
		for (const entity of [
			{ file_name: 'Notes.txt' },
			{ file_name: 'Ancien.doc' },
			{ file_name: 'Ancien.xls' },
			{ file_name: 'Calc.ods' },
			{ file_name: 'Sans extension' },
			{ file_name: 'Dossier.docx', is_folder: 1 },
			{ file_name: 'Lien.pdf', is_link: 1 },
			{ file_name: 'Page.docx', file_type: 'Document' },
			null,
		]) {
			expect(opensInNeodesk(entity)).toBe(false)
		}
	})

	it('is only where the site has the editor of the type', () => {
		const installed = { word: '0.8.0', pdf: '0.7.1' }
		expect(editorInstalledFor({ file_name: 'a.docx' }, installed)).toBe(true)
		expect(editorInstalledFor({ file_name: 'a.pdf' }, installed)).toBe(true)
		expect(editorInstalledFor({ file_name: 'a.xlsx' }, installed)).toBe(false)
		expect(editorInstalledFor({ file_name: 'a.docx' }, null)).toBe(false)
		expect(editorInstalledFor({ file_name: 'a.txt' }, { word: '0.8.0' })).toBe(false)
	})

	it('is on a computer only, never a phone or a tablet', () => {
		const mac = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15'
		const windows = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36'
		expect(isDesktopBrowser({ userAgent: mac, maxTouchPoints: 0 })).toBe(true)
		expect(isDesktopBrowser({ userAgent: windows, maxTouchPoints: 0 })).toBe(true)
		// An iPad says « Macintosh », with a touch screen.
		expect(isDesktopBrowser({ userAgent: mac, maxTouchPoints: 5 })).toBe(false)
		expect(
			isDesktopBrowser({ userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Mobile/15E148', maxTouchPoints: 5 }),
		).toBe(false)
		expect(isDesktopBrowser({ userAgent: 'Mozilla/5.0 (Linux; Android 15) Chrome/141.0 Mobile Safari/537.36' })).toBe(false)
		expect(isDesktopBrowser({ userAgent: windows, userAgentData: { mobile: true } })).toBe(false)
		// Linux: no Neodesk there.
		expect(isDesktopBrowser({ userAgent: 'Mozilla/5.0 (X11; Linux x86_64) Firefox/140.0' })).toBe(false)
		expect(isDesktopBrowser(undefined)).toBe(false)
	})
})

describe('« Don\'t show again »', () => {
	it('is kept in the browser, and read back', () => {
		const kept = new Map<string, string>()
		const storage = { getItem: (k: string) => kept.get(k) ?? null, setItem: (k: string, v: string) => void kept.set(k, v) }
		expect(hintHidden(storage)).toBe(false)
		hideHint(storage)
		expect(kept.get(HINT_HIDDEN_KEY)).toBe('1')
		expect(hintHidden(storage)).toBe(true)
	})

	it('never breaks the page where the browser keeps nothing', () => {
		const refusing = {
			getItem: () => {
				throw new Error('SecurityError')
			},
			setItem: () => {
				throw new Error('QuotaExceededError')
			},
		}
		expect(() => hideHint(refusing)).not.toThrow()
		expect(hintHidden(refusing)).toBe(false)
	})
})

describe('trying the address', () => {
	beforeEach(() => vi.useFakeTimers())
	afterEach(() => vi.useRealTimers())

	/** A window and a document that write down what the page does with them. */
	function page() {
		const win = new EventTarget() as EventTarget & Record<string, unknown>
		const doc = new EventTarget() as EventTarget & { visibilityState: string }
		doc.visibilityState = 'visible'
		const location = { href: 'https://osiris.neoffice.me/drive/f/ab12' }
		Object.assign(win, { location, setTimeout, clearTimeout })
		return { win, doc, location }
	}

	it('hands the address over at once, within the click, and says « Nothing opened? » when nothing happened', () => {
		const { win, doc, location } = page()
		const onNothing = vi.fn()
		tryNeodesk('neodesk://drive/osiris.neoffice.me/ab12', { win, doc, onNothing })
		expect(location.href).toBe('neodesk://drive/osiris.neoffice.me/ab12')
		vi.advanceTimersByTime(NOTHING_OPENED_AFTER_MS - 1)
		expect(onNothing).not.toHaveBeenCalled()
		vi.advanceTimersByTime(1)
		expect(onNothing).toHaveBeenCalledTimes(1)
	})

	it('says nothing when the page lost the focus or was hidden: Neodesk came to the front', () => {
		for (const happen of [
			(p: ReturnType<typeof page>) => p.win.dispatchEvent(new Event('blur')),
			(p: ReturnType<typeof page>) => p.win.dispatchEvent(new Event('pagehide')),
			(p: ReturnType<typeof page>) => {
				p.doc.visibilityState = 'hidden'
				p.doc.dispatchEvent(new Event('visibilitychange'))
			},
		]) {
			const p = page()
			const onNothing = vi.fn()
			tryNeodesk('neodesk://drive/osiris.neoffice.me/ab12', { win: p.win, doc: p.doc, onNothing })
			happen(p)
			vi.advanceTimersByTime(NOTHING_OPENED_AFTER_MS)
			expect(onNothing).not.toHaveBeenCalled()
		}
	})

	it('a page that shows again without having hidden is not taken for Neodesk', () => {
		const p = page()
		const onNothing = vi.fn()
		tryNeodesk('neodesk://drive/osiris.neoffice.me/ab12', { win: p.win, doc: p.doc, onNothing })
		p.doc.dispatchEvent(new Event('visibilitychange'))
		vi.advanceTimersByTime(NOTHING_OPENED_AFTER_MS)
		expect(onNothing).toHaveBeenCalledTimes(1)
	})

	it('stops watching when the page goes away first', () => {
		const p = page()
		const onNothing = vi.fn()
		const stop = tryNeodesk('neodesk://drive/osiris.neoffice.me/ab12', { win: p.win, doc: p.doc, onNothing })
		stop()
		vi.advanceTimersByTime(NOTHING_OPENED_AFTER_MS)
		expect(onNothing).not.toHaveBeenCalled()
	})

	it('offers the official download', () => {
		expect(NEODESK_DOWNLOAD_URL).toBe('https://github.com/bvisible/neoffice-desktop-releases/releases/latest')
	})
})
