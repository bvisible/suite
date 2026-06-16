import type { RouteRecordRaw } from 'vue-router'

/**
 * Writer route module — the CONTRACT a per-app port implements.
 *
 * Export a `routes` array RELATIVE to the '/writer' prefix (paths WITHOUT a
 * leading slash; the empty-path child '' is the app index). The suite router
 * mounts this array under '/writer' lazily on first navigation. Add views under
 * src/apps/writer/views, components under src/apps/writer/components, composables
 * under src/apps/writer/composables, and any app store under
 * src/apps/writer/stores. Keep heavy deps lazy via `() => import(...)`.
 */
export const routes: RouteRecordRaw[] = [
  {
    path: '',
    name: 'writer-home',
    component: () => import('@/apps/writer/views/WriterStub.vue'),
  },
]

export default routes
