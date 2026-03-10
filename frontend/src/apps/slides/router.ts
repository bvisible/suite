import { createRouter, createWebHistory, RouteLocationNormalized } from 'vue-router'

import { createResource } from 'frappe-ui'

import { session } from '@/stores/session'

const withPresentationProps = (route: RouteLocationNormalized) => {
	const slide = parseInt(route.query.slide as string)
	const activeSlideId = Number.isFinite(slide) ? slide : 1

	return {
		presentationId: route.params.presentationId,
		activeSlideId: activeSlideId,
		editorAccess: editorAccess,
	}
}

const routes = [
	{
		path: '/',
		name: 'Home',
		component: () => import('@/pages/Home.vue'),
	},
	{
		path: '/presentation/new',
		name: 'EditorNew',
		component: () => import('@/pages/PresentationEditor.vue'),
		props: withPresentationProps,
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
		path: '/slideshow/:presentationId/:slug?',
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

const getEditorAccess = async (presentationId: string) => {
	try {
		const response = await createResource({
			url: "slides.slides.doctype.presentation.presentation.get_editor_access",
			method: "GET",
		}).submit({
			doctype: "Presentation",
			presentation_id: presentationId,
		})
		return response
	} catch (error) {
		console.error('Failed to fetch presentation access level:', error)
		return false
	}
}

let previousRoute = null
let editorAccess = "none"

router.beforeEach(async (to, from, next) => {
	previousRoute = from

	const isLoggedIn = session.isLoggedIn

	if (!['Slideshow', 'PresentationEditor', 'Home'].includes(to.name as string)) {
		return next()
	}

	if (to.name === 'Slideshow' && !from.name) {
		return next({ name: 'PresentationEditor', params: to.params, query: to.query } )
	} else if (to.name === 'Slideshow') {
		return next()
	} else if (to.name === 'PresentationEditor') {
		if (from.name != to.name || from.params.presentationId != to.params.presentationId) {
			editorAccess = await getEditorAccess(to.params.presentationId as string)
		}
		if (['edit', 'view'].includes(editorAccess)) {
			return next()
		}
		else {
			return next({ name: 'NotPermitted' })
		}
	} else {
		if (!isLoggedIn) {
			if (to.path !== '/login') window.location.href = '/login?redirect-to=' + to.path
			return next()
		}

		return next()
	}
})

export { router, previousRoute, editorAccess }
