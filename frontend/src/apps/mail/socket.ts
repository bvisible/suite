import { io } from 'socket.io-client'
import { getCachedListResource, getCachedResource } from 'frappe-ui'

declare global {
	interface Window {
		site_name?: string
	}
}

export const initSocket = () => {
	const host = window.location.hostname
	const siteName = window.site_name || host
	const socketio_port = __SOCKETIO_PORT__
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
