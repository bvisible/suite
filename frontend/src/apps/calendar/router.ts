import { createRouter, createWebHistory } from 'vue-router'

import { sessionStore } from '@/stores/session'

import type { UserAccount } from '@/types/doctypes'

import { userStore } from './stores/user'

const ShortcutRedirect = { render: () => null }

const routes = [
	{
		path: '/account/:accountId/month/:year?/:month?/:day?',
		name: 'Month',
		component: () => import('@/pages/CalendarView.vue'),
	},
	{
		path: '/account/:accountId/week/:year?/:month?/:day?',
		name: 'Week',
		component: () => import('@/pages/CalendarView.vue'),
	},
	{
		path: '/account/:accountId/day/:year?/:month?/:day?',
		name: 'Day',
		component: () => import('@/pages/CalendarView.vue'),
	},
	// Shortcut routes: short paths that resolve to their full account-scoped
	// equivalents once the active accountId is known (resolved in beforeEach).
	{
		path: '/',
		name: 'RootShortcut',
		component: ShortcutRedirect,
		meta: { shortcut: true },
	},
	{
		path: '/account/:accountId?',
		name: 'AccountShortcut',
		component: ShortcutRedirect,
		meta: { shortcut: true },
	},
	{
		path: '/month/:year?/:month?/:day?',
		name: 'MonthShortcut',
		component: ShortcutRedirect,
		meta: { shortcut: true },
	},
	{
		path: '/week/:year?/:month?/:day?',
		name: 'WeekShortcut',
		component: ShortcutRedirect,
		meta: { shortcut: true },
	},
	{
		path: '/day/:year?/:month?/:day?',
		name: 'DayShortcut',
		component: ShortcutRedirect,
		meta: { shortcut: true },
	},
]

const router = createRouter({ history: createWebHistory('/calendar'), routes })

const handleSetupWizardEscape = () => {
	if (document.referrer.includes('/app/setup-wizard')) window.location.replace('/app')
}

const getPersonalAccountId = (user: { accounts?: UserAccount[] }) =>
	user.accounts?.find((a) => a.is_personal)?.id

const resolveAccount = (
	routeAccountId: string | undefined,
	user: { accounts?: UserAccount[] },
	storeAccountId: string,
	setAccount: (id: string) => void,
) => {
	if (routeAccountId) {
		const isValid = user.accounts?.some((a) => a.id === routeAccountId)
		if (isValid) {
			if (routeAccountId !== storeAccountId) setAccount(routeAccountId)
			return
		}
	}

	if (!storeAccountId) {
		const personalId = getPersonalAccountId(user)
		if (personalId) setAccount(personalId)
	}
}

const resolveShortcut = (
	name: string | symbol | null | undefined,
	params: Record<string, string | string[]>,
	accountId: string,
) => {
	const defaultRoute = { name: 'Month', params: { accountId } }

	switch (name) {
		case 'MonthShortcut':
			return { name: 'Month', params: { accountId, ...params } }
		case 'WeekShortcut':
			return { name: 'Week', params: { accountId, ...params } }
		case 'DayShortcut':
			return { name: 'Day', params: { accountId, ...params } }
		default:
			return defaultRoute
	}
}

router.beforeEach(async (to) => {
	handleSetupWizardEscape()

	// 1. Authentication check
	const { isLoggedIn } = sessionStore()
	if (!isLoggedIn) window.location.replace('/mail/login')

	// 2. Wait for user data
	const { userResource, setAccount } = userStore()
	await userResource.promise
	const user = userResource.data

	// Re-read accountId after resolveAccount may have updated it via setAccount
	const accountId = userStore().accountId

	// 3. Resolve active account
	resolveAccount(to.params.accountId as string | undefined, user, accountId, setAccount)

	// 4. Expand shortcut routes to their full account-scoped equivalents
	if (to.meta.shortcut) return resolveShortcut(to.name, to.params, accountId)
})

export default router
