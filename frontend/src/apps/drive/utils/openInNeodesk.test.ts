//// Neoffice — added file (no upstream equivalent): tests of utils/openInNeodesk.js, « Ouvrir dans Neodesk ».
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, reactive, ref } from 'vue'

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
	useOpenInNeodesk,
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
		expect(neodeskLink({ ...site, hostname: '10.0.0.5' }, 'ab12')).toBeNull()
		expect(neodeskLink({ ...site, hostname: '[::1]' }, 'ab12')).toBeNull()
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

	const CHROME = { userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36' }
	const FIREFOX = { userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:140.0) Gecko/20100101 Firefox/140.0' }

	/** A window and a document that write down what the page does with them (Chrome's, unless told). */
	function page(nav: { userAgent: string } = CHROME) {
		const win = new EventTarget() as EventTarget & Record<string, unknown>
		const doc = new EventTarget() as EventTarget & {
			visibilityState: string
			body: HTMLElement
			createElement: Document['createElement']
		}
		doc.visibilityState = 'visible'
		doc.body = document.createElement('div')
		doc.createElement = document.createElement.bind(document)
		const location = { href: 'https://osiris.neoffice.me/drive/f/ab12' }
		Object.assign(win, { location, setTimeout, clearTimeout, navigator: nav })
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

	it('Firefox: the address goes to a hidden frame, never to the page, which an address nobody takes could replace', () => {
		const { win, doc, location } = page(FIREFOX)
		const onNothing = vi.fn()
		tryNeodesk('neodesk://drive/osiris.neoffice.me/ab12', { win, doc, onNothing })
		expect(location.href).toBe('https://osiris.neoffice.me/drive/f/ab12')
		const frame = doc.body.querySelector('iframe')
		expect(frame?.getAttribute('src')).toBe('neodesk://drive/osiris.neoffice.me/ab12')
		expect(frame?.style.display).toBe('none')
		expect(frame?.getAttribute('aria-hidden')).toBe('true')
		vi.advanceTimersByTime(NOTHING_OPENED_AFTER_MS)
		// The quiet « Nothing opened? » all the same, and the frame gone with the watch.
		expect(onNothing).toHaveBeenCalledTimes(1)
		expect(doc.body.querySelector('iframe')).toBeNull()
	})

	it('Firefox: the frame goes too when the page leaves first', () => {
		const { win, doc } = page(FIREFOX)
		const stop = tryNeodesk('neodesk://drive/osiris.neoffice.me/ab12', { win, doc })
		stop()
		expect(doc.body.querySelector('iframe')).toBeNull()
	})

	it('Chrome, Edge and Safari keep the page when no program takes the address: no frame there', () => {
		for (const nav of [CHROME, { userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15' }]) {
			const { win, doc, location } = page(nav)
			tryNeodesk('neodesk://drive/osiris.neoffice.me/ab12', { win, doc })
			expect(location.href).toBe('neodesk://drive/osiris.neoffice.me/ab12')
			expect(doc.body.querySelector('iframe')).toBeNull()
		}
	})

	it('offers the official download', () => {
		expect(NEODESK_DOWNLOAD_URL).toBe('https://github.com/bvisible/neoffice-desktop-releases/releases/latest')
	})
})

describe("the file page's button (components/Navbar.vue, through useOpenInNeodesk)", () => {
	beforeEach(() => vi.useFakeTimers())
	afterEach(() => vi.useRealTimers())

	const MAC = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36'

	/** The page as the bar sees it, every part of it a test's to change; a browser that keeps what it is told. */
	function bar({ name = 'drive-File', signedIn = true, framed = false, file = 'Devis.docx', editors = { word: '0.7.0' } } = {}) {
		const kept = new Map<string, string>()
		const win = new EventTarget() as EventTarget & Record<string, unknown>
		const doc = new EventTarget() as EventTarget & { visibilityState: string; body: HTMLElement; createElement: Document['createElement'] }
		doc.visibilityState = 'visible'
		doc.body = document.createElement('div')
		doc.createElement = document.createElement.bind(document)
		const location = { protocol: 'https:', hostname: 'osiris.neoffice.me', port: '', href: 'https://osiris.neoffice.me/drive/f/ab12cd' }
		Object.assign(win, {
			location,
			setTimeout,
			clearTimeout,
			navigator: { userAgent: MAC, maxTouchPoints: 0 },
			localStorage: { getItem: (k: string) => kept.get(k) ?? null, setItem: (k: string, v: string) => void kept.set(k, v) },
		})
		const route = reactive({ name })
		const entity = ref(file ? { name: 'ab12cd', file_name: file, is_folder: 0 } : null)
		const installedEditors = reactive({ data: null as Record<string, string> | null, loading: false, fetch: vi.fn() })
		installedEditors.fetch.mockImplementation(() => {
			installedEditors.data = editors
		})
		const scope = effectScope()
		const it = scope.run(() =>
			useOpenInNeodesk({ route, entity, isLoggedIn: ref(signedIn), inIframe: framed, installedEditors, win, doc }),
		)!
		return { it, scope, route, entity, installedEditors, location, win, kept }
	}

	it('offers the address of the file on its own page, once the site said it has the editor', () => {
		const { it: button, installedEditors, scope } = bar()
		expect(installedEditors.fetch).toHaveBeenCalledTimes(1)
		expect(button.link.value).toBe('neodesk://drive/osiris.neoffice.me/ab12cd')
		scope.stop()
	})

	it('offers nothing elsewhere: a folder page, signed out, framed, another type, an editor the site has not', () => {
		for (const [options, why] of [
			[{ name: 'drive-Folder' }, 'not a file page'],
			[{ signedIn: false }, 'signed out'],
			[{ framed: true }, 'framed'],
			[{ file: 'Notes.txt' }, 'a .txt'],
			[{ file: 'Ventes.xlsx' }, 'no NeoGrille on the site'],
			[{ file: '' }, 'no file yet'],
		] as const) {
			const { it: button, scope } = bar(options as Record<string, unknown>)
			expect(button.link.value, why).toBeNull()
			scope.stop()
		}
		// The editors are not asked for where the button cannot be
		const away = bar({ name: 'drive-Folder' })
		expect(away.installedEditors.fetch).not.toHaveBeenCalled()
		away.scope.stop()
	})

	it('a click hands the address over; « Nothing opened? » after the wait; « Don\'t show again » is kept', () => {
		const { it: button, location, scope, kept } = bar()
		button.open()
		expect(location.href).toBe('neodesk://drive/osiris.neoffice.me/ab12cd')
		vi.advanceTimersByTime(NOTHING_OPENED_AFTER_MS)
		expect(button.hint.value).toBe(true)
		button.never()
		expect(button.hint.value).toBe(false)
		expect(kept.get(HINT_HIDDEN_KEY)).toBe('1')
		button.open()
		vi.advanceTimersByTime(NOTHING_OPENED_AFTER_MS)
		expect(button.hint.value).toBe(false)
		scope.stop()
	})

	it('the hint goes by itself when Neodesk comes after the browser\'s question, and nothing stays when the page goes', () => {
		const { it: button, win, scope } = bar()
		button.open()
		vi.advanceTimersByTime(NOTHING_OPENED_AFTER_MS)
		expect(button.hint.value).toBe(true)
		win.dispatchEvent(new Event('blur'))
		expect(button.hint.value).toBe(false)
		// A click, then the page leaves before the wait ends: no hint later
		button.open()
		scope.stop()
		vi.advanceTimersByTime(NOTHING_OPENED_AFTER_MS)
		expect(button.hint.value).toBe(false)
	})
})
