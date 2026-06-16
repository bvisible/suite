import suiteRouter from '@/router'

/**
 * Writer router compat shim.
 *
 * The standalone Writer app had its own `createRouter`. In the suite there is
 * ONE router (mounted at '/', writer routes live under '/writer'); auth is
 * handled by the suite router's own `beforeEach` (redirects guests to /login
 * unless the route is `meta.isPublic`, which `writer-document` is).
 *
 * Writer has no app-specific navigation guard to install, so this module only
 * re-exports the single suite router instance as the default export, mirroring
 * the calendar/meet/slides ports, so writer utils that read
 * `router.currentRoute` keep working.
 */
export const router = suiteRouter

export default suiteRouter
