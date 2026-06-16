import type { RouteRecordRaw } from 'vue-router'

/**
 * Meet route module — the CONTRACT a per-app port implements.
 *
 * Export a `routes` array RELATIVE to the '/meet' prefix (paths WITHOUT a
 * leading slash; the empty-path child '' is the app index). The suite router
 * mounts this array under '/meet' lazily on first navigation. Add views under
 * src/apps/meet/views, components under src/apps/meet/components, composables
 * under src/apps/meet/composables, and any app store under
 * src/apps/meet/stores. Keep heavy deps lazy via `() => import(...)`.
 */
export const routes: RouteRecordRaw[] = [
  {
    path: '',
    name: 'meet-home',
    component: () => import('@/apps/meet/views/MeetStub.vue'),
  },
]

export default routes
