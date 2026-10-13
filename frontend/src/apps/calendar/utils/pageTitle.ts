// //// Neoffice — added file (no upstream equivalent): the title of the calendar page as Neodesk writes it (canvas
// //// « Neodesk », board 11): « Octobre 2026 » in the month and the week, « Semaine 42 » beside it in the week, the
// //// day in full in the day view.

type DayjsDate = {
	format: (pattern: string) => string
	isSame: (other: DayjsDate, unit: 'month' | 'year') => boolean
	toDate: () => Date
}
type Dayjs = (date?: string) => DayjsDate

/** The period the calendar shows, as its `range-change` reports it. */
export type VisibleRange = { view: string; startDate: string; endDate: string } | null

export const capitalized = (text: string) => text.charAt(0).toUpperCase() + text.slice(1)

/** ISO 8601 week number: week 1 holds the year's first Thursday. */
export function isoWeek(date: Date): number {
	const day = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))
	day.setUTCDate(day.getUTCDate() + 4 - (day.getUTCDay() || 7))
	return Math.ceil(((day.getTime() - Date.UTC(day.getUTCFullYear(), 0, 1)) / 86400000 + 1) / 7)
}

/**
 * `monthYear` is frappe-ui's own label of the month view; `week` the word for a week in the reader's language. A week
 * across two months names both (« Septembre – octobre 2026 »), across two years both years.
 */
export function pageTitle(range: VisibleRange, monthYear: string, dayjs: Dayjs, week: string) {
	if (range?.view === 'Day') {
		const day = dayjs(range.startDate)
		return { title: capitalized(`${day.format('dddd')} ${day.format('LL')}`), sub: '' }
	}
	if (range?.view === 'Week') {
		const start = dayjs(range.startDate)
		const end = dayjs(range.endDate)
		const months = start.isSame(end, 'month')
			? start.format('MMMM YYYY')
			: `${start.format(start.isSame(end, 'year') ? 'MMMM' : 'MMMM YYYY')} – ${end.format('MMMM YYYY')}`
		return { title: capitalized(months), sub: `${week} ${isoWeek(start.toDate())}` }
	}
	return { title: capitalized(monthYear || ''), sub: '' }
}
