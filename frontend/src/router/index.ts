import {
  createRouter,
  createWebHistory,
  type RouteRecordRaw,
} from 'vue-router'

import { SUITE_APPS } from '@/apps/registry'
import { useSessionStore } from '@/boot/session'

/**
 * ONE Vue Router for the whole suite.
 *
 * Each of the 7 apps contributes a route GROUP mounted at its original prefix
 * (/drive /slides /writer /sheets /meet /mail /calendar). Every group lazy-loads
 * `src/apps/<id>/routes.ts`, which exports a `routes: RouteRecordRaw[]` array
 * RELATIVE to that prefix (paths without a leading slash; the empty-path child
 * is the app's index). This keeps per-app bundles code-split so the shell stays
 * small (heavy app deps — mediasoup, firebase, xlsx, docx — load only on demand).
 *
 * `/suite` is the launcher (app switcher).
 *
 * Lazy registration: each app's prefix initially resolves to a placeholder
 * record carrying `meta.appId`. The first navigation into a prefix loads that
 * app's route module, replaces the placeholder with a real group containing the
 * module's `routes`, and re-resolves the navigation (see `beforeEach`).
 */

// Dynamic-import loaders for each app's route module. The import is a dynamic
// `import()` so the app's actual views/components stay code-split.
const appRouteLoaders: Record<string, () => Promise<{ routes: RouteRecordRaw[] }>> = {
  drive: () => import('@/apps/drive/routes'),
  slides: () => import('@/apps/slides/routes'),
  writer: () => import('@/apps/writer/routes'),
  sheets: () => import('@/apps/sheets/routes'),
  meet: () => import('@/apps/meet/routes'),
  mail: () => import('@/apps/mail/routes'),
  calendar: () => import('@/apps/calendar/routes'),
}

// Placeholder record per app: matches the prefix + everything under it and
// carries `meta.appId`. `beforeEach` swaps it for the real routes on first hit.
const placeholderGroups: RouteRecordRaw[] = SUITE_APPS.map((app) => ({
  path: `${app.prefix}/:pathMatch(.*)*`,
  name: `${app.id}-placeholder`,
  component: () => import('@/shell/AppContainer.vue'),
  meta: { appId: app.id },
}))

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/suite',
  },
  {
    path: '/suite',
    name: 'suite-launcher',
    component: () => import('@/shell/LauncherView.vue'),
    meta: { isShell: true },
  },
  ...placeholderGroups,
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/shell/NotFoundView.vue'),
  },
]

const router = createRouter({
  // Served at site root; the SPA owns all the app prefixes below '/'.
  history: createWebHistory('/'),
  routes,
})

// Apps whose real route groups have already been registered.
const registeredApps = new Set<string>()

/**
 * Load `src/apps/<appId>/routes.ts`, register its routes under the app prefix
 * inside an AppContainer group, and drop the placeholder so future navigations
 * resolve straight to the real routes.
 */
async function ensureAppRoutesLoaded(appId: string): Promise<void> {
  if (registeredApps.has(appId)) return

  const loader = appRouteLoaders[appId]
  const app = SUITE_APPS.find((a) => a.id === appId)
  if (!loader || !app) return

  const mod = await loader()

  router.addRoute({
    path: app.prefix,
    component: () => import('@/shell/AppContainer.vue'),
    meta: { appId },
    children: mod.routes,
  })

  // Remove the catch-all placeholder so it no longer shadows the real routes.
  if (router.hasRoute(`${appId}-placeholder`)) {
    router.removeRoute(`${appId}-placeholder`)
  }

  registeredApps.add(appId)
}

router.beforeEach(async (to) => {
  // 1. Lazy-load the target app's route module before resolving the route.
  const appId = to.meta.appId as string | undefined
  if (appId && !registeredApps.has(appId)) {
    await ensureAppRoutesLoaded(appId)
    // Re-resolve now that the real routes exist.
    return { path: to.fullPath, replace: true }
  }

  // 2. Auth gate (shell launcher + every app require a logged-in user).
  const session = useSessionStore()
  if (!session.isLoggedIn && !to.meta.isPublic) {
    window.location.href = `/login?redirect-to=${encodeURIComponent(to.fullPath)}`
    return false
  }

  return true
})

export default router
