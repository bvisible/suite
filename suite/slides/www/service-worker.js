const CACHE_NAME = 'slides-private-files'
const MAX_AGE = 24 * 60 * 60 * 1000 // 1 day

self.addEventListener('install', () => {
	self.skipWaiting()
})

const cleanupOldCacheEntry = async (cache, request, response) => {
	const now = Date.now()

	const cachedTimeHeader = response.headers.get('x-cached-time')
	if (!cachedTimeHeader) return

	const cachedTime = parseInt(cachedTimeHeader, 10)
	if (isNaN(cachedTime)) return

	const age = now - cachedTime

	if (age > MAX_AGE) {
		await cache.delete(request)
	}
}

const cleanupOldCache = async () => {
	const cache = await caches.open(CACHE_NAME)
	const keys = await cache.keys()

	await Promise.all(
		keys.map(async (request) => {
			const response = await cache.match(request)
			if (!response) return

			cleanupOldCacheEntry(cache, request, response)
		}),
	)
}

const handleSWActivate = async () => {
	cleanupOldCache()
	// this takes control of all client pages that are already open
	await self.clients.claim()
}

self.addEventListener('activate', (event) => {
	event.waitUntil(handleSWActivate())
})

const getModifiedResponse = (response) => {
	const responseToCache = response.clone()
	const headers = new Headers(responseToCache.headers)
	headers.set('x-cached-time', Date.now().toString())

	return new Response(responseToCache.body, {
		status: responseToCache.status,
		statusText: responseToCache.statusText,
		headers: headers,
	})
}

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
					if (ct.startsWith('image/')) {
						// Clone response and add cache timestamp header
						const modifiedResponse = getModifiedResponse(response)
						cache.put(request, modifiedResponse)
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
