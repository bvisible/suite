import { createRouter, createWebHistory } from 'vue-router'
import { session } from '@/stores/session'

const routes = [
	{
		path: '/',
		name: 'Home',
		component: () => import('@/pages/Home.vue'),
	},
	{
		path: '/:presentationId',
		name: 'Presentation',
		component: () => import('@/pages/Presentation.vue'),
	},
]

let router = createRouter({
	history: createWebHistory('/slides'),
	routes,
})

router.beforeEach(async (to, _, next) => {
	let isLoggedIn = session.isLoggedIn
	if (to.path === '/login' && isLoggedIn) {
		next({ name: 'Home' })
	} else if (to.path !== '/login' && !isLoggedIn) {
		window.location.href = '/login?redirect-to=' + to.path
	} else {
		next()
	}
})

export default router
