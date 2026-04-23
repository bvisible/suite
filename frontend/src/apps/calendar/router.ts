import { createRouter, createWebHistory } from 'vue-router'

import { sessionStore } from '@/stores/session'

const routes = [
	{
		path: '/',
		redirect: { name: 'Month' },
	},
	{
		path: '/month/:year?/:month?/:day?',
		name: 'Month',
		component: () => import('@/pages/CalendarView.vue'),
	},
	{
		path: '/week/:year?/:month?/:day?',
		name: 'Week',
		component: () => import('@/pages/CalendarView.vue'),
	},
	{
		path: '/day/:year?/:month?/:day?',
		name: 'Day',
		component: () => import('@/pages/CalendarView.vue'),
	},
]

const router = createRouter({ history: createWebHistory('/calendar'), routes })

router.beforeEach(() => {
	if (document.referrer.includes('/app/setup-wizard')) window.location.replace('/app')

	const { isLoggedIn } = sessionStore()
	if (!isLoggedIn) window.location.replace('/mail/login')
})

export default router
