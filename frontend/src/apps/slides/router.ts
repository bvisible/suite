import type { RouteLocationNormalized } from 'vue-router'

import suiteRouter from '@/router'

/**
 * Slides router compat shim.
 *
 * The standalone slides app had its own `createRouter` and exported
 * `{ router, previousRoute, editorAccess }`. In the suite there is ONE router
 * (mounted at '/', slides routes live under '/slides'); this shim re-exports
 * that single instance as `router` so slides' module-singleton stores can keep
 * calling `router.replace(...)` / `router.currentRoute`, and tracks the
 * `previousRoute` + per-presentation `editorAccess` that slides' views read.
 *
 * The actual tracking/guard is installed from `routes.ts` (`installSlidesGuards`)
 * which runs once the slides route module is lazy-loaded.
 */
export const router = suiteRouter

export let previousRoute: RouteLocationNormalized | null = null
export let editorAccess = 'none'

export function setPreviousRoute(route: RouteLocationNormalized | null) {
  previousRoute = route
}

export function setEditorAccess(access: string) {
  editorAccess = access
}
