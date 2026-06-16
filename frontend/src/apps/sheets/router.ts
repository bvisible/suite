import suiteRouter from '@/router'

/**
 * Sheets router compat shim.
 *
 * The standalone Sheets app had NO vue-router — it hand-rolled
 * `history.pushState` + a `?id=` query param to swap between the Home listing
 * and the editor. Under the suite there is ONE router (mounted at '/', sheets
 * routes live under '/sheets'); this shim re-exports that single instance so
 * any non-component module in sheets can navigate without reaching back into
 * the bespoke history API. Views/composables should prefer `useRouter()` /
 * `useRoute()`; this exists for the few module-scope helpers that can't.
 */
export const router = suiteRouter

/** Absolute URL for a sheet by id — used when opening a sheet in a new tab. */
export function sheetUrl(id: string): string {
  return `${window.location.origin}/sheets/${encodeURIComponent(id)}`
}
