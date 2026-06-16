import type { RouteRecordRaw } from 'vue-router'

/**
 * Drive route module — the CONTRACT a per-app port implements.
 *
 * Export a `routes` array RELATIVE to the '/drive' prefix (paths WITHOUT a
 * leading slash; the empty-path child '' is the app index). The suite router
 * mounts this array under '/drive' lazily on first navigation. Add views under
 * src/apps/drive/views, components under src/apps/drive/components, composables
 * under src/apps/drive/composables, and any app store under
 * src/apps/drive/stores. Keep heavy deps lazy via `() => import(...)`.
 */
export const routes: RouteRecordRaw[] = [
  {
    path: '',
    name: 'drive-home',
    component: () => import('@/apps/drive/views/DriveStub.vue'),
  },
]

export default routes
