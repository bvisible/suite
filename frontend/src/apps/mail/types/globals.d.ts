export {}

// The global `__` translate helper is provided by the suite foundation
// (src/env.d.ts + the global translation plugin), so it is NOT re-declared
// here to avoid a conflicting duplicate declaration.

declare global {
	interface Window {
		/** FCM push-notification client, set up by the mail module's SW registration. */
		frappePushNotification?: import('@/apps/mail/utils/frappe-push-notification').default
		/** Notification relay server base URL (Frappe push notifications). */
		push_relay_server_url: string
	}
}
