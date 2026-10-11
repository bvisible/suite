//// Neoffice — added file (no upstream equivalent): the dates of the ERP, read-only in the calendar (maintenance#1428).
//// Suite's calendar adds them to the list of calendars and to the events (suite/calendar/sources.py): a calendar or an
//// event with `virtual` set. This is how the page tells them apart from the person's own, and what it does with them.

/** The calendar's palette (frappe-ui's colour map) has no red: a date that is late draws in its closest, pink. */
export const LATE_PALETTE = 'pink'

export const isErpCalendar = (calendar: any): boolean => !!calendar?.virtual

export const isErpEvent = (event: any): boolean => !!event?.virtual

/**
 * The colour of a dot in the sidebar. A palette name ('green') is a colour of frappe-ui's map, not of CSS ('amber'
 * and 'violet' are not CSS colours): it is drawn with the ink variable the grid itself uses. Anything else (a hex)
 * is already a colour.
 */
export const swatch = (colour?: string | null): string | undefined => {
	if (!colour) return undefined
	return /^[a-z]+$/.test(colour) ? `var(--ink-${colour}-6)` : colour
}

/** The palette an event of the grid is drawn in: late ones in pink, the others in their source's colour. */
export const erpEventPalette = (event: any, sourcePalette?: string | null): string | undefined =>
	event?.late ? LATE_PALETTE : sourcePalette || event?.palette || undefined

/**
 * Where the document of a date opens: a page of the desk. Only a path of this site is followed, whatever the server
 * says (an address of another site, or a script, would be an open door).
 */
export const erpEventRoute = (event: any): string => {
	const route = String(event?.route || '')
	return /^\/app\/[^\s]*$/.test(route) ? route : ''
}
