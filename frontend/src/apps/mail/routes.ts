import type { RouteRecordRaw } from 'vue-router'

/**
 * Mail route module — the CONTRACT a per-app port implements.
 *
 * Export a `routes` array RELATIVE to the '/mail' prefix (paths WITHOUT a
 * leading slash; the empty-path child '' is the app index). The suite router
 * mounts this array under '/mail' lazily on first navigation. Add views under
 * src/apps/mail/views, components under src/apps/mail/components, composables
 * under src/apps/mail/composables, and any app store under
 * src/apps/mail/stores. Keep heavy deps lazy via `() => import(...)`.
 */
export const routes: RouteRecordRaw[] = [
  {
    path: '',
    name: 'mail-home',
    component: () => import('@/apps/mail/views/MailStub.vue'),
  },
]

export default routes
