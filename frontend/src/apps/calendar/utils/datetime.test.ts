import { describe, expect, it, vi } from 'vitest'

import dayjs from '@/apps/calendar/utils/dayjs'

vi.mock('@/apps/calendar/stores/user', () => ({
	userStore: () => ({ userResource: { data: { time_zone: 'Asia/Karachi' } } }),
}))

// The browser zone wins over the User doc's zone; the tests below assert against it.
vi.spyOn(dayjs.tz, 'guess').mockReturnValue('Asia/Kolkata')

const load = async () => await import('@/apps/calendar/utils/datetime')

describe('calendar datetime helpers', () => {
	it('prefers the browser zone, falling back to the user zone', async () => {
		const { userTimeZone } = await load()
		expect(userTimeZone()).toBe('Asia/Kolkata')
		vi.mocked(dayjs.tz.guess).mockReturnValueOnce(undefined as unknown as string)
		expect(userTimeZone()).toBe('Asia/Karachi')
	})

	it('renders a UTC timestamp in the user zone', async () => {
		const { formatDateTime } = await load()
		expect(formatDateTime('2026-07-28T09:02:30Z')).toBe('Jul 28 2026, 2:32 PM')
	})

	it('reads an alert wall clock back as UTC', async () => {
		const { fromWallClock } = await load()
		expect(fromWallClock('2026-07-28T14:32')).toBe('2026-07-28T09:02:00Z')
	})

	it('round-trips an alert through the user zone', async () => {
		const { fromWallClock, inUserTimeZone } = await load()
		const when = fromWallClock('2026-07-28T14:32')
		expect(inUserTimeZone(when).format('YYYY-MM-DDTHH:mm')).toBe('2026-07-28T14:32')
	})

	it('moves an event wall clock into the viewer zone', async () => {
		const { fromEventZone } = await load()
		// 2 PM Asia/Kolkata is 10:30 AM in Vienna; the viewer here is Asia/Kolkata, so a
		// Vienna-stored 10:30 AM renders back at 2 PM.
		expect(fromEventZone('2026-07-29T10:30:00', 'Europe/Vienna').format('HH:mm')).toBe('14:00')
		expect(fromEventZone('2026-07-29T14:00:00', 'Asia/Kolkata').format('HH:mm')).toBe('14:00')
	})

	it('leaves a floating event where the viewer is', async () => {
		const { fromEventZone } = await load()
		expect(fromEventZone('2026-07-29T14:00:00', null).format('HH:mm')).toBe('14:00')
		expect(fromEventZone('2026-07-29T14:00:00', '').format('HH:mm')).toBe('14:00')
	})

	it('leaves blanks blank', async () => {
		const { formatDateTime, fromWallClock } = await load()
		expect(formatDateTime(null)).toBe('')
		expect(fromWallClock('')).toBe('')
	})
})
