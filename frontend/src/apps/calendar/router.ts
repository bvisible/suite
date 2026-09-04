import type { RouteLocationNormalized, Router } from 'vue-router'

//// Neoffice — added for the on-demand mailbox provisioning in the guard below
//// (a desk user must always end up with a calendar). Upstream just bounces to
//// the no-account page.
import { frappeRequest } from 'frappe-ui'

import suiteRouter from '@/router'

import { userStore } from '@/apps/calendar/stores/user'

/**
 * Calendar-local guard on the shared suite router: setup-wizard escape,
 * user-data wait, account resolution and shortcut-route expansion.
 * Early-returns for any route whose name doesn't start with `calendar-`;
 * auth itself is the suite router's `beforeEach`.
 *
 * Re-exports the suite router instance as `router` for calendar views.
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

		// //// Neoffice: a desk user must ALWAYS have a calendar. If they arrive
		// without a JMAP account, provision their mailbox on demand (covers the
		// brief async window after signup / a missed backfill) BEFORE falling
		// back to the informational page. Website (client) users get no mailbox
		// and land on calendar-no-account. Guard against a re-entry loop by only
		// trying when we're not already on the no-account page. ////
		if (!accountId) {
			if (to.name !== 'calendar-no-account') {
				try {
					const ok = await frappeRequest({
						url: 'suite.mail.events.ensure_personal_mail_account',
					})
					if (ok) {
						await store.userResource.reload()
						store.resolveAccount(
							store.userResource.data?.accounts,
							to.params.accountId as string | undefined,
						)
						if (store.accountId) {
							return to.meta.shortcut
								? resolveShortcut(to.name, to.params, store.accountId)
								: undefined
						}
					}
				} catch (e) {
					// fall through to the informational page
				}
				return { name: 'calendar-no-account' }
			}
			return undefined // already on no-account, stay
		}

		// Expand shortcut routes to their full account-scoped equivalents. The
		// query rides along — it carries the open event's deep link (?event=).
		if (to.meta.shortcut) return { ...resolveShortcut(to.name, to.params, accountId), query: to.query }
	})
}

installCalendarGuard(router)

export default router
