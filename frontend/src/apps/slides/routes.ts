import type { RouteLocationNormalized, RouteRecordRaw, Router } from 'vue-router'

import { createResource } from 'frappe-ui'

import { router, setEditorAccess, setPreviousRoute } from '@/apps/slides/router'

/**
 * Slides route module — mounted by the suite router under the '/slides' prefix.
 *
 * Paths are RELATIVE to '/slides' (no leading slash; '' is the app index).
 * Route names are namespaced `slides-*` to avoid collisions in the single
 * suite router. Views are lazy so slides' heavy editor deps stay code-split.
 *
 * Names map from the standalone app: Home -> slides-home,
 * EditorNew -> slides-editor-new, PresentationEditor -> slides-editor,
 * Slideshow -> slides-slideshow, NotPermitted -> slides-not-permitted.
 */

const withPresentationProps = (route: RouteLocationNormalized) => {
  const slide = parseInt(route.query.slide as string)
  const activeSlideId = Number.isFinite(slide) ? slide : 1

  return {
    presentationId: route.params.presentationId,
    activeSlideId,
    editorAccess: currentEditorAccess,
  }
}

export const routes: RouteRecordRaw[] = [
  {
    path: '',
    name: 'slides-home',
    component: () => import('@/apps/slides/views/Home.vue'),
  },
  {
    path: 'presentation/new',
    name: 'slides-editor-new',
    component: () => import('@/apps/slides/views/PresentationEditor.vue'),
    props: withPresentationProps,
  },
  {
    path: 'presentation/:presentationId/:slug?',
    name: 'slides-editor',
    component: () => import('@/apps/slides/views/PresentationEditor.vue'),
    props: withPresentationProps,
  },
  {
    path: 'presentation/view/:presentationId/:slug?',
    redirect: (route: RouteLocationNormalized) => ({
      name: 'slides-editor',
      params: route.params,
      query: route.query,
    }),
  },
  {
    path: 'slideshow/:presentationId/:slug?',
    name: 'slides-slideshow',
    component: () => import('@/apps/slides/views/Slideshow.vue'),
    props: withPresentationProps,
  },
  {
    path: 'not-permitted',
    name: 'slides-not-permitted',
    component: () => import('@/apps/slides/views/errorPages/NotPermitted.vue'),
  },
]

export default routes

/* -------------------------------------------------------------------------- */
/* Slides navigation guards                                                    */
/*                                                                             */
/* Ported from the standalone app's router.beforeEach: maintain `previousRoute`*/
/* and gate the editor route on the per-presentation access level. Installed   */
/* once, the first time this module is loaded (see bottom of file).            */
/* -------------------------------------------------------------------------- */

let currentEditorAccess = 'none'

const getEditorAccess = async (presentationId: string) => {
  try {
    const response = await createResource({
      url: 'slides.slides.doctype.presentation.presentation.get_editor_access',
      method: 'GET',
    }).submit({
      doctype: 'Presentation',
      presentation_id: presentationId,
    })
    return response
  } catch (error) {
    console.error('Failed to fetch presentation access level:', error)
    return false
  }
}

const SLIDES_GUARDED = new Set(['slides-slideshow', 'slides-editor', 'slides-home'])

function installSlidesGuards(r: Router) {
  r.beforeEach(async (to, from, next) => {
    // Only act on slides routes; let the suite handle everything else.
    if (typeof to.name !== 'string' || !to.name.startsWith('slides-')) {
      return next()
    }

    setPreviousRoute(from)

    if (!SLIDES_GUARDED.has(to.name)) {
      return next()
    }

    if (to.name === 'slides-slideshow' && !from.name) {
      return next({ name: 'slides-editor', params: to.params, query: to.query })
    } else if (to.name === 'slides-slideshow') {
      return next()
    } else if (to.name === 'slides-editor') {
      if (from.name !== to.name || from.params.presentationId !== to.params.presentationId) {
        currentEditorAccess = (await getEditorAccess(to.params.presentationId as string)) as string
        setEditorAccess(currentEditorAccess)
      }
      if (['edit', 'view'].includes(currentEditorAccess)) {
        return next()
      }
      return next({ name: 'slides-not-permitted' })
    }
    return next()
  })
}

installSlidesGuards(router)
