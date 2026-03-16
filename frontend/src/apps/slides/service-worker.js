const MEDIA_CACHE_NAME = 'slides-media'
const version = '__BUILD_TIMESTAMP__'
const ASSET_CACHE_NAME = `slides-assets-v${version}`
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

const cleanupOldMediaCache = async () => {
	const cache = await caches.open(MEDIA_CACHE_NAME)
	const keys = await cache.keys()

	await Promise.all(
		keys.map(async (request) => {
			const response = await cache.match(request)
			if (!response) return

			return cleanupOldCacheEntry(cache, request, response)
		}),
	)
}

const cleanupOldAssetCache = async () => {
	const cacheNames = await caches.keys()
	await Promise.all(
		cacheNames.map((cacheName) => {
			if (cacheName.startsWith('slides-assets') && cacheName !== ASSET_CACHE_NAME) {
				return caches.delete(cacheName)
			}
		}),
	)
}

const cleanupOldCaches = () => {
	cleanupOldAssetCache()
	cleanupOldMediaCache()
}

const handleSWActivate = async () => {
	cleanupOldCaches()
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
	return (
		url.pathname.startsWith('/private/files/') ||
		url.pathname.startsWith('/api/method/slides.api.file.get_media_file')
	)
}
const isAsset = (url) => url.pathname.startsWith('/assets/') || url.pathname.startsWith('/slides/')
const isAPI = (url) =>
	url.pathname.startsWith('/api/method/frappe.client.') ||
	url.pathname.startsWith('/api/method/slides.slides.')

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
		if (!validContentTypes.some((ct) => contentType.startsWith(ct))) return
	}

	// clone response and add cache timestamp header
	const modifiedResponse = getModifiedResponse(response)
	await cache.put(request, modifiedResponse)
}

const fetchAndCache = async (request, type, cache) => {
	const response = await fetch(request)
	if (response.ok && response.status === 200) {
		await addCacheEntry(type, cache, request, response)
	}
	return response
}

const getResponseForRequest = async (request, type) => {
	const cache = await getCacheObject(type)

	if (type === 'api') {
		try {
			await fetchAndCache(request, type, cache)
		} catch {
			const cached = await cache.match(request)
			if (cached) return cached
			throw new Error('No cached response available')
		}
	}

	const cached = await cache.match(request)
	if (cached) return cached
	return await fetchAndCache(request, type, cache)
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

	if (request.method !== 'GET' || url.origin !== self.location.origin) return

	const requestType = getRequestType(url)
	const isAffectedByCache = ['media', 'asset', 'api'].includes(requestType)
	if (!isAffectedByCache) return

	const response = getResponseForRequest(request, requestType)
	event.respondWith(response)
}

self.addEventListener('fetch', (event) => {
	handleSWFetch(event)
})
