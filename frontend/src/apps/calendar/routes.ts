import type { RouteRecordRaw } from 'vue-router'

/**
 * Calendar route module — the CONTRACT a per-app port implements.
 *
 * Export a `routes` array RELATIVE to the '/calendar' prefix (paths WITHOUT a
 * leading slash; the empty-path child '' is the app index). The suite router
 * mounts this array under '/calendar' lazily on first navigation. Add views under
 * src/apps/calendar/views, components under src/apps/calendar/components, composables
 * under src/apps/calendar/composables, and any app store under
 * src/apps/calendar/stores. Keep heavy deps lazy via `() => import(...)`.
 */
export const routes: RouteRecordRaw[] = [
  {
    path: '',
    name: 'calendar-home',
    component: () => import('@/apps/calendar/views/CalendarStub.vue'),
  },
]

export default routes
