import { createRouter, createWebHistory } from 'vue-router'
import { session } from '@/stores/session'

const routes = [
	{
		path: '/',
		name: 'Home',
		component: () => import('@/pages/Home.vue'),
	},
	{
		path: '/presentation/:presentationId',
		name: 'PresentationEditor',
		component: () => import('@/pages/PresentationEditor.vue'),
	},
	{
		path: '/slideshow/:presentationId',
		name: 'Slideshow',
		component: () => import('@/pages/Slideshow.vue'),
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
