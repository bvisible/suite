import type { RouteLocationNormalized, Router } from 'vue-router'

import suiteRouter from '@/router'

import { userStore } from '@/apps/calendar/stores/user'

/**
 * Calendar router compat + guard.
 *
 * The standalone calendar app had its own `createRouter` with a global
 * `beforeEach` that did: setup-wizard escape, auth, user-data wait, ACCOUNT
 * RESOLUTION and SHORTCUT-ROUTE EXPANSION. In the suite there is ONE router
 * (mounted at '/', calendar routes live under '/calendar'); auth is handled by
 * the suite router's own `beforeEach` (redirects guests to `/login`). So only
 * the calendar-SPECIFIC parts are ported here as a calendar-local guard that
 * early-returns for any route whose name doesn't start with `calendar-`.
 *
 * This re-exports the single suite router instance as `router` so calendar views
 * can keep importing it if needed, mirroring the slides reference port.
 */
export const router = suiteRouter

type Params = Record<string, string | string[]>

const resolveShortcut = (
	name: string | symbol | null | undefined,
	params: Params,
	accountId: string,
) => {
	const defaultRoute = { name: 'calendar-month', params: { accountId } }

	switch (name) {
		case 'calendar-month-shortcut':
			return { name: 'calendar-month', params: { accountId, ...params } }
		case 'calendar-week-shortcut':
			return { name: 'calendar-week', params: { accountId, ...params } }
		case 'calendar-day-shortcut':
			return { name: 'calendar-day', params: { accountId, ...params } }
		default:
			return defaultRoute
	}
}

function installCalendarGuard(r: Router) {
	r.beforeEach(async (to: RouteLocationNormalized) => {
		// Only act on calendar routes; let the suite handle everything else.
		if (typeof to.name !== 'string' || !to.name.startsWith('calendar-')) return

		// Wait for user data, then resolve the active account.
		const store = userStore()
		await store.userResource.promise
		const user = store.userResource.data

		store.resolveAccount(user?.accounts, to.params.accountId as string | undefined)
		const accountId = store.accountId

		// Expand shortcut routes to their full account-scoped equivalents.
		if (to.meta.shortcut) return resolveShortcut(to.name, to.params, accountId)
	})
}

installCalendarGuard(router)

export default router
