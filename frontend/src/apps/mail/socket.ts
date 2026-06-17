import { io } from 'socket.io-client'
import { getCachedListResource, getCachedResource } from 'frappe-ui'

// `socketio_port` was imported from sites/common_site_config.json in the
// standalone app — a path OUTSIDE the suite frontend root that Vite's fs.allow
// rejects. Read it from window boot data instead, with a dev fallback. The
// Window augmentation is declared locally (not in the shared env.d.ts).
declare global {
	interface Window {
		site_name?: string
		socketio_port?: number | string
	}
}

export const initSocket = () => {
	const host = window.location.hostname
	const siteName = window.site_name || host
	const socketio_port = window.socketio_port ?? 9000
	const port = window.location.port ? `:${socketio_port}` : ''
	const protocol = port ? 'http' : 'https'
	const url = `${protocol}://${host}${port}/${siteName}`

	const socket = io(url, { withCredentials: true, reconnectionAttempts: 5 })
	socket.on('refetch_resource', (data) => {
		if (data.cache_key) {
			const resource =
				getCachedResource(data.cache_key) || getCachedListResource(data.cache_key)
			if (resource) resource.reload()
		}
	})
	return socket
}
