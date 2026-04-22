import { createRouter, createWebHistory } from 'vue-router'

import { sessionStore } from '@/stores/session'

const routes = [
	{
		path: '/',
		redirect: { name: 'Month' },
	},
	{
		path: '/month',
		name: 'Month',
		component: () => import('@/pages/CalendarView.vue'),
	},
	{
		path: '/week',
		name: 'Week',
		component: () => import('@/pages/CalendarView.vue'),
	},
	{
		path: '/day',
		name: 'Day',
		component: () => import('@/pages/CalendarView.vue'),
	},
]

const router = createRouter({ history: createWebHistory('/calendar'), routes })

router.beforeEach((_, __, next) => {
	if (document.referrer.includes('/app/setup-wizard')) window.location.replace('/app')

	const { isLoggedIn } = sessionStore()
	if (!isLoggedIn) window.location.replace('/mail/login')

	return next()
})

export default router
