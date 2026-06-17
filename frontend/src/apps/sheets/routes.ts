import type { RouteRecordRaw } from 'vue-router'

/**
 * Sheets route module — mounted by the suite router under the '/sheets' prefix.
 *
 * The standalone app had NO vue-router: it toggled between the Home listing and
 * the editor with `history.pushState` + a `?id=` query param. That is replaced
 * here with two real routes:
 *
 *   ''       -> sheets-home    (the listing; was `?id` absent)
 *   ':id'    -> sheets-editor  (the editor; was `?id=<name>`, `?id=new` => /sheets/new)
 *
 * Paths are RELATIVE to '/sheets' (no leading slash; '' is the app index).
 * Route names are namespaced `sheets-*` to avoid collisions in the single suite
 * router. Views are lazy so the heavy editor deps (xlsx, echarts, yjs) stay
 * code-split out of the shared shell bundle.
 */
export const routes: RouteRecordRaw[] = [
  {
    path: '',
    name: 'sheets-home',
    component: () => import('@/apps/sheets/pages/Home.vue'),
  },
  {
    path: ':id',
    name: 'sheets-editor',
    component: () => import('@/apps/sheets/pages/SheetEditor.vue'),
    props: true,
  },
]

export default routes
