import type { RouteRecordRaw } from 'vue-router'

import { createResource } from 'frappe-ui'

// Install the calendar-local navigation guard (account resolution + shortcut
// expansion) on the shared suite router. Importing for side effects only.
import '@/apps/calendar/router'

/**
 * Calendar route module — mounted by the suite router under the '/calendar'
 * prefix. Paths are RELATIVE to '/calendar' (no leading slash; the empty-path
 * child '' is the app index). Route names are namespaced `calendar-*` to avoid
 * collisions in the single suite router.
 *
 * Name mapping from the standalone app:
 *   Month          -> calendar-month
 *   Week           -> calendar-week
 *   Day            -> calendar-day
 *   RootShortcut   -> calendar-root-shortcut
 *   AccountShortcut-> calendar-account-shortcut
 *   MonthShortcut  -> calendar-month-shortcut
 *   WeekShortcut   -> calendar-week-shortcut
 *   DayShortcut    -> calendar-day-shortcut
 *
 * The shortcut routes resolve to their full account-scoped equivalents in the
 * calendar guard once the active accountId is known (see ./router.ts). They use
 * a no-op render component since the guard always redirects them.
 *
 * All real routes nest under a layout route (CalendarLayout) which provides the
 * calendar-local `$user` / `$dayjs` injections the views depend on.
 */

const ShortcutRedirect = { render: () => null }

export const routes: RouteRecordRaw[] = [
	{
		path: '',
		component: () => import('@/apps/calendar/views/CalendarLayout.vue'),
		children: [
			{
				path: 'account/:accountId/month/:year?/:month?/:day?',
				name: 'calendar-month',
				component: () => import('@/apps/calendar/views/CalendarView.vue'),
			},
			{
				path: 'account/:accountId/week/:year?/:month?/:day?',
				name: 'calendar-week',
				component: () => import('@/apps/calendar/views/CalendarView.vue'),
			},
			{
				path: 'account/:accountId/day/:year?/:month?/:day?',
				name: 'calendar-day',
				component: () => import('@/apps/calendar/views/CalendarView.vue'),
			},
			// Shortcut routes: short paths that resolve to their full account-scoped
			// equivalents once the active accountId is known (resolved in the guard).
			{
				path: '',
				name: 'calendar-root-shortcut',
				component: ShortcutRedirect,
				meta: { shortcut: true },
			},
			{
				path: 'account/:accountId?',
				name: 'calendar-account-shortcut',
				component: ShortcutRedirect,
				meta: { shortcut: true },
			},
			{
				path: 'month/:year?/:month?/:day?',
				name: 'calendar-month-shortcut',
				component: ShortcutRedirect,
				meta: { shortcut: true },
			},
			{
				path: 'week/:year?/:month?/:day?',
				name: 'calendar-week-shortcut',
				component: ShortcutRedirect,
				meta: { shortcut: true },
			},
			{
				path: 'day/:year?/:month?/:day?',
				name: 'calendar-day-shortcut',
				component: ShortcutRedirect,
				meta: { shortcut: true },
			},
		],
	},
]

export default routes

/* -------------------------------------------------------------------------- */
/* Translations                                                                */
/*                                                                             */
/* The suite installs ONE global translation plugin (foundation                */
/* src/boot/translation.ts) so bare `__('text')` works everywhere. We only     */
/* need to populate `window.translatedMessages`. Port calendar's translations  */
/* fetch as a side-effect on module load. Backend method path preserved as-is. */
/* -------------------------------------------------------------------------- */

const translations = createResource({
	url: 'suite.mail.api.get_translations',
	cache: 'translations',
	transform: (data) => (window.translatedMessages = data),
})

if (!window.translatedMessages) translations.fetch()
