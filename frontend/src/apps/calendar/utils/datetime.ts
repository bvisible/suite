import dayjs from '@/apps/calendar/utils/dayjs'
import { userStore } from '@/apps/calendar/stores/user'

/**
 * Timestamps on the wire are always UTC, spelled the way Stalwart spells them:
 * "2026-07-28T09:02:30Z". This is the calendar counterpart of
 * `@/apps/mail/utils/datetime` — the single place that moves between that wire format and the
 * zone the user reads and types in. JSCalendar `start`/`duration`/`timeZone` values are local
 * time plus an IANA zone and never pass through here.
 */

const UTC_FORMAT = 'YYYY-MM-DDTHH:mm:ss[Z]'

/**
 * The zone timestamps are displayed and typed in: the browser's, falling back to `time_zone` on
 * the User doc for the rare environment where the browser cannot say (`get_user_info` resolves
 * that to the site's zone when unset, completing the browser → user → system fallback chain).
 */
export const userTimeZone = (): string => {
	const { userResource } = userStore()
	return dayjs.tz.guess() || userResource.data?.time_zone
}

/** Reads a UTC timestamp from an API into the user's zone. */
export const inUserTimeZone = (value: string) => dayjs.utc(value).tz(userTimeZone())

/** Formats a UTC timestamp from an API for display in the user's zone. */
export const formatDateTime = (value?: string | null, format = 'MMM D YYYY, h:mm A'): string =>
	value ? inUserTimeZone(value).format(format) : ''

/**
 * Turns a wall-clock reading in the user's zone (e.g. an alert's date + time inputs, carrying
 * no offset) into the UTC timestamp the APIs take. Blank stays blank so callers can tell
 * "unset" from a time.
 */
export const fromWallClock = (value?: string | null): string =>
	value ? dayjs.tz(value, userTimeZone()).utc().format(UTC_FORMAT) : ''

/**
 * Reads a JSCalendar `start` — a wall clock in the event's own IANA zone — into the user's
 * zone, so a 2 PM Asia/Kolkata event renders at 10:30 AM in Vienna. An event without a zone
 * is floating and stays wherever the viewer is.
 */
export const fromEventZone = (start: string, eventTimeZone?: string | null) =>
	eventTimeZone ? dayjs.tz(start, eventTimeZone).tz(userTimeZone()) : dayjs(start)

/** The start of a `YYYY-MM-DD` day in the user's zone, as a UTC timestamp the APIs take. */
export const utcDayStart = (date?: string | null): string =>
	date ? dayjs.tz(date, userTimeZone()).startOf('day').utc().format(UTC_FORMAT) : ''

/** The end of a `YYYY-MM-DD` day in the user's zone, as a UTC timestamp the APIs take. */
export const utcDayEnd = (date?: string | null): string =>
	date ? dayjs.tz(date, userTimeZone()).endOf('day').utc().format(UTC_FORMAT) : ''
