import suiteRouter from '@/router'
import { setActiveEntity } from '@/apps/drive/data/selection'

/**
 * Drive-local navigation guard on the shared suite router, scoped to `drive-*`
 * routes so it never runs for other apps:
 *   - clears the active entity on every navigation,
 *   - stores the current route in sessionStorage.
 * Auth itself is the suite router's `beforeEach` (redirects guests for
 * non-`meta.allowGuest` routes).
 *
 * Re-exports the suite router instance for drive utils that read
 * `router.currentRoute` / call `router.push`.
 */
const isDriveRoute = (route: { name?: unknown; path?: string }) =>
  (typeof route.name === 'string' && route.name.startsWith('drive-')) ||
  (route.path?.startsWith('/drive') ?? false)

suiteRouter.beforeEach((to, _from, next) => {
  if (!isDriveRoute(to)) return next()
  setActiveEntity(null)
  next()
})

suiteRouter.afterEach((to) => {
  if (!isDriveRoute(to)) return
  sessionStorage.setItem('currentRoute', to.href)
})

export const router = suiteRouter
export default suiteRouter
