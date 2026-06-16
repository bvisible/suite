<template>
	<FrappeUIProvider>
		<component :is="Layout">
			<router-view />
		</component>
		<InstallPrompt v-if="isMobile" />
	</FrappeUIProvider>
</template>

<script setup lang="ts">
import { computed, onMounted, provide, watchEffect } from 'vue'
import { useRoute } from 'vue-router'
import { FrappeUIProvider } from 'frappe-ui'

import { useScreenSize, useTheme } from '@/apps/mail/utils/composables'
import { showNotification } from '@/apps/mail/utils/push-notifications'
import { initSocket } from '@/apps/mail/socket'
import dayjs from '@/apps/mail/utils/dayjs'
import { userStore } from '@/apps/mail/stores/user'
import DefaultLayout from '@/apps/mail/components/DefaultLayout.vue'
import InstallPrompt from '@/apps/mail/components/InstallPrompt.vue'

import type { NotificationPayload } from '@/apps/mail/types'

/**
 * Mail route-group layout.
 *
 * Maps the standalone app's root App.vue. The suite shell already provides the
 * top-level chrome and main.ts provides Pinia/router/frappe-ui/translation, but
 * does NOT provide mail's `$user` / `$dayjs` / `$socket` injects, register
 * mail's push-notification SW, or set up mail's theme. So this layout:
 *   - provides the mail-local `$user` / `$dayjs` / `$socket` injections,
 *   - applies the user's color scheme to <html data-theme>,
 *   - picks the inner layout (DefaultLayout / bare div for noLayout routes),
 *   - wires push-notification onMessage and registers the (fail-safe) SW,
 *   - wraps children in FrappeUIProvider and renders the nested <router-view>.
 *
 * Public pre-auth routes (login/signup/...) sit OUTSIDE this layout since they
 * do not need the $user/$dayjs/$socket injects.
 */
const { userResource } = userStore()
const { dataTheme } = useTheme()
const { isMobile } = useScreenSize()
const route = useRoute()

provide('$user', userResource)
provide('$dayjs', dayjs)
provide('$socket', initSocket())

const Layout = computed(() => {
	if (route.meta.noLayout) return 'div'
	return DefaultLayout
})

watchEffect(() => document.documentElement.setAttribute('data-theme', dataTheme.value))

/* -------------------------------------------------------------------------- */
/* Push-notification service worker.                                          */
/*                                                                            */
/* Moved out of the standalone main.ts. The suite has NO vite-plugin-pwa, so  */
/* `/assets/suite/frontend/sw.js` is NOT emitted yet — push notifications     */
/* will not function at runtime under the suite until a foundation PWA/FCM    */
/* setup lands (flagged for foundation attention). Kept FULLY fail-safe so it */
/* never breaks the build or first paint. `firebase` is dynamically imported  */
/* so it stays code-split out of the shared shell chunk.                      */
/* -------------------------------------------------------------------------- */
const registerServiceWorker = async () => {
	try {
		if (!('serviceWorker' in navigator)) return

		const { default: FrappePushNotification } = await import(
			'@/apps/mail/utils/frappe-push-notification'
		)
		window.frappePushNotification = new FrappePushNotification('mail')

		let serviceWorkerURL = '/assets/suite/frontend/sw.js'
		let config: unknown = ''

		try {
			config = await window.frappePushNotification.fetchWebConfig()
			serviceWorkerURL = `${serviceWorkerURL}?config=${encodeURIComponent(
				JSON.stringify(config),
			)}`
		} catch (err) {
			console.error('Failed to fetch FCM config', err)
		}

		const registration = await navigator.serviceWorker.register(serviceWorkerURL, {
			type: 'module',
		})
		if (config)
			window.frappePushNotification
				.initialize(registration)
				.then(() => console.log('Frappe Push Notification initialized'))
	} catch (err) {
		console.error('Failed to register service worker', err)
	}
}

onMounted(() => {
	registerServiceWorker()
	window.frappePushNotification?.onMessage((payload: NotificationPayload) =>
		showNotification(payload),
	)
})
</script>

<style>
/* Global mail styles ported from the standalone src/index.css. The suite's
   global css already imports frappe-ui/style.css, so we only carry the mail
   base type sizing + the shared `.icon` helper. frappe-ui design tokens are
   referenced via their CSS variables (NOT @apply, which would break the build
   for these plugin-registered token classes). */
.mail-app-root {
	color: var(--ink-gray-8);
	background-color: var(--surface-base);
}

.icon {
	stroke-width: 1.5;
	width: 1rem;
	height: 1rem;
	color: var(--ink-gray-6);
}
</style>
