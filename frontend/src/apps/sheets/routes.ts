import type { RouteRecordRaw } from 'vue-router'

/**
 * Sheets route module — the CONTRACT a per-app port implements.
 *
 * Export a `routes` array RELATIVE to the '/sheets' prefix (paths WITHOUT a
 * leading slash; the empty-path child '' is the app index). The suite router
 * mounts this array under '/sheets' lazily on first navigation. Add views under
 * src/apps/sheets/views, components under src/apps/sheets/components, composables
 * under src/apps/sheets/composables, and any app store under
 * src/apps/sheets/stores. Keep heavy deps lazy via `() => import(...)`.
 */
export const routes: RouteRecordRaw[] = [
  {
    path: '',
    name: 'sheets-home',
    component: () => import('@/apps/sheets/views/SheetsStub.vue'),
  },
]

export default routes
