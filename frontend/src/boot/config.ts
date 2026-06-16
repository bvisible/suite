import { frappeRequest, setConfig } from 'frappe-ui'

/**
 * Unified frappe-ui resource configuration for the whole suite.
 *
 * All 7 apps share ONE API base: requests go to the Frappe site that serves
 * this SPA (suite.localhost). frappe-ui's `frappeRequest` reads
 * `window.csrf_token` (injected by index.html / suite.html) and talks to
 * `/api/method/...` on the same origin, so per-app fetch wrappers
 * (sheets/utils/api.js, drive resourceFetcher overrides, etc.) collapse onto
 * this single configuration.
 *
 * Call `configureFrappeUI()` exactly once, before mounting the app.
 */
export function configureFrappeUI() {
  setConfig('resourceFetcher', frappeRequest)
}

/** Shared API base used by raw fetch/socket helpers that bypass frappe-ui. */
export const API_BASE = '/api/method'
