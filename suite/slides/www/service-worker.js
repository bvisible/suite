const CACHE_NAME = 'slides-private-files-v1'

self.addEventListener('activate', (event) => {
	event.waitUntil(
		(async () => {
			// this takes control of the client page basically
			await self.clients.claim()
		})(),
	)
})

self.addEventListener('fetch', (event) => {
	const request = event.request
	if (request.method !== 'GET') return

	// before fetching, check if it's a file request
	const url = new URL(request.url)

	if (url.origin !== self.location.origin) return
	if (!url.pathname.startsWith('/private/files/')) return

	event.respondWith(
		(async () => {
			// if the image is there in the cache, don't fetch from network
			const cache = await caches.open(CACHE_NAME)
			const cached = await cache.match(request, { ignoreSearch: false })
			if (cached) return cached

			// else fetch from network and cache it
			try {
				const response = await fetch(request)

				// check for valid response here - basically avoid caching if 404 or other error
				if (response.ok && response.status === 200) {
					const ct = response.headers.get('content-type') || ''
					// Avoid caching HTML/error pages
					if (ct.startsWith('image/')) {
						cache.put(request, response.clone())
					}
				}
				return response
			} catch (err) {
				// if fetch fails, return cached version if available
				// if there's no cached version, throw missing error
				if (cached) return cached
				throw err
			}
		})(),
	)
})
