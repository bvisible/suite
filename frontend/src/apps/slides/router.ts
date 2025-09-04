import { createRouter, createWebHistory, RouteLocationNormalized } from 'vue-router'

import { createResource } from 'frappe-ui'

import { session } from '@/stores/session'

const withPresentationProps = (route: RouteLocationNormalized) => {
	const slide = parseInt(route.query.slide as string)
  	const activeSlideId = Number.isFinite(slide) ? slide : 1

	return {
		presentationId: route.params.presentationId,
		activeSlideId: activeSlideId,
	}
}


const routes = [
	{
		path: '/',
		name: 'Home',
		component: () => import('@/pages/Home.vue'),
	},
	{
		path: '/presentation/:presentationId/:slug?',
		name: 'PresentationEditor',
		component: () => import('@/pages/PresentationEditor.vue'),
		props: withPresentationProps,
	},
	{
		path: '/presentation/view/:presentationId/:slug?',
		name: 'PresentationView',
		component: () => import('@/pages/PresentationEditor.vue'),
		props: withPresentationProps,
	},
	{
		path: '/slideshow/:presentationId',
		name: 'Slideshow',
		component: () => import('@/pages/Slideshow.vue'),
		props: withPresentationProps,
	},
	{
		path: '/not-permitted',
		name: 'NotPermitted',
		component: () => import('@/pages/errorPages/NotPermitted.vue'),
	}
]

let router = createRouter({
	history: createWebHistory('/slides'),
	routes,
})

const hasAccess = async (presentationId: string) => {
	if (!session.isLoggedIn) return false
	try {
		const response = await createResource({
			url: "frappe.client.has_permission",
			method: "GET",
		}).submit({
			doctype: "Presentation",
			docname: presentationId,
			perm_type: "write",
		})
		return response.has_permission
	} catch (error) {
		console.error('Permission check failed:', error)
		return false
	}
}

const isPublicPresentation = async (presentationId: string) => {
	try {
		const response = await createResource({
			url: "slides.slides.doctype.presentation.presentation.is_public_presentation",
			method: "GET",
		}).submit({
			doctype: "Presentation",
			name: presentationId,
		})
		return response
	} catch (error) {
		console.error('Failed to fetch presentation access level:', error)
		return false
	}
}

let previousRoute = null


router.beforeEach(async (to, from, next) => {
	previousRoute = from

	const isLoggedIn = session.isLoggedIn

	if (isLoggedIn && to.path === '/login') {
		return next({ name: 'Home' })
	}

	const protectedRoutes = ['PresentationEditor', 'Slideshow', 'PresentationView', 'Home']
	if (!protectedRoutes.includes(to.name as string)) {
		return next()
	}

	if (['Slideshow', 'PresentationView', 'PresentationEditor'].includes(to.name as string)) {
		const canAccess = await hasAccess(to.params.presentationId as string)
		if (canAccess && ['PresentationEditor', 'Slideshow'].includes(to.name as string)) {
			if (to.name === 'Slideshow' && !from.name) {
				return next({ name: 'PresentationEditor', params: to.params, query: to.query } )
			}
			return next()
		} else if (canAccess) {
			return next({ name: 'PresentationEditor', params: to.params, query: to.query } )
		}
		else {
			const isPublic = await isPublicPresentation(to.params.presentationId as string)
			if (isPublic && ['Slideshow', 'PresentationView'].includes(to.name as string)) {
				if (to.name === 'Slideshow' && !from.name) {
					return next({ name: 'PresentationView', params: to.params, query: to.query } )
				}
				return next()
			} else if (isPublic) {
				return next({ name: 'PresentationView', params: to.params, query: to.query } )
			} else {
				return next({ name: 'NotPermitted' })
			}
		}
	}

	if (!isLoggedIn) {
		if (to.path !== '/login') window.location.href = '/login?redirect-to=' + to.path
		return next()
	}

	if (session.isSlidesUser === null) {
		await session.setIsSlidesUser()
	}

	if (!session.isSlidesUser && to.name !== 'NotPermitted') {
		return next({ name: 'NotPermitted' })
	}
	return next()
})

export { router, previousRoute }
