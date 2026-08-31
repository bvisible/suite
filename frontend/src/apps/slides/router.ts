import type { RouteLocationNormalized } from 'vue-router'

import suiteRouter from '@/router'

/**
 * Slides router shim: re-exports the single suite router instance as `router`
 * for slides' module-singleton stores, and tracks the `previousRoute` +
 * per-presentation `editorAccess` that slides' views read.
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
