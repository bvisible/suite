const MEDIA_CACHE_NAME = 'slides-media'
const ASSET_CACHE_NAME = 'slides-assets'
const API_CACHE_NAME = 'slides-api'

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
	const cache = await caches.open(MEDIA_CACHE_NAME)
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

const isMedia = (url) => {
	return url.pathname.startsWith('/private/files/')
}
const isAsset = (url) => url.pathname.startsWith('/assets/')
const isAPI = (url) => url.pathname.startsWith('/api/')

const getCacheObject = async (type) => {
	switch (type) {
		case 'asset':
			return await caches.open(ASSET_CACHE_NAME)
		case 'media':
			return await caches.open(MEDIA_CACHE_NAME)
		case 'api':
			return await caches.open(API_CACHE_NAME)
		default:
			return null
	}
}

const addCacheEntry = async (type, cache, request, response) => {
	if (type === 'media') {
		const contentType = response.headers.get('Content-Type') || ''
		const validContentTypes = ['image/', 'video/']
		if (!validContentTypes.includes(contentType)) return
	}

	// clone response and add cache timestamp header
	const modifiedResponse = getModifiedResponse(response)
	cache.put(request, modifiedResponse)
}

const getResponseForRequest = async (request, type) => {
	const cache = await getCacheObject(type)
	const url = new URL(request.url)

	if (type === 'api') {
		try {
			const response = await fetch(request)
			if (response.ok && response.status === 200) {
				addCacheEntry(type, cache, request, response)
			}
			return response
		} catch {
			// Network failed, try cache
			const cached = await cache.match(request)
			if (cached) return cached
			throw new Error('No cached API response available')
		}
	}

	const cached = await cache.match(request)
	if (cached) return cached

	// else fetch from network and cache it
	const response = await fetch(request)

	if (response.ok && response.status === 200) {
		// if a valid response, cache it
		addCacheEntry(type, cache, request, response)
	}

	return response
}

const getRequestType = (url) => {
	if (isMedia(url)) return 'media'
	if (isAsset(url)) return 'asset'
	if (isAPI(url)) return 'api'
	return 'other'
}

const handleSWFetch = async (event) => {
	const request = event.request

	const url = new URL(request.url)
	const isDocGet = url.pathname.includes('/api/method/frappe.client.get')

	if (request.method !== 'GET' && !isDocGet) return
	if (url.origin !== self.location.origin) return

	const requestType = getRequestType(url)
	const isAffectedByCache = ['media', 'asset', 'api'].includes(requestType)
	if (!isAffectedByCache) return

	const response = getResponseForRequest(request, requestType)
	event.respondWith(response)
}

self.addEventListener('fetch', (event) => {
	handleSWFetch(event)
})
