import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'

/**
 * Calendar-local branding store.
 *
 * Ported from the standalone app's `stores/session.ts`, which fetched
 * `suite.mail.api.get_branding` and set the favicon. The auth/logout concerns of that
 * store are handled by the shared suite session store (`@/boot/session`); only
 * the calendar-specific branding fetch lives here. Backend method path is
 * preserved as-is (endpoint reconciliation is a later phase).
 */
export const brandingStore = defineStore('calendar-branding', () => {
	const branding = createResource({
		url: 'suite.mail.api.get_branding',
		cache: 'brand',
		auto: true,
		onSuccess: (data) => {
			const icon = document.querySelector<HTMLLinkElement>("link[rel='icon']")
			if (icon && data?.favicon) icon.href = data.favicon
		},
	})

	return { branding }
})
