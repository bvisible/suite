(function() {
	//#region node_modules/.pnpm/workbox-core@7.4.1/node_modules/workbox-core/_version.js
	try {
		self["workbox:core:7.4.0"] && _();
	} catch (e) {}
	//#endregion
	//#region node_modules/.pnpm/workbox-core@7.4.1/node_modules/workbox-core/models/messages/messageGenerator.js
	var fallback = (code, ...args) => {
		let msg = code;
		if (args.length > 0) msg += ` :: ${JSON.stringify(args)}`;
		return msg;
	};
	var messageGenerator = fallback;
	//#endregion
	//#region node_modules/.pnpm/workbox-core@7.4.1/node_modules/workbox-core/_private/WorkboxError.js
	/**
	* Workbox errors should be thrown with this class.
	* This allows use to ensure the type easily in tests,
	* helps developers identify errors from workbox
	* easily and allows use to optimise error
	* messages correctly.
	*
	* @private
	*/
	var WorkboxError = class extends Error {
		/**
		*
		* @param {string} errorCode The error code that
		* identifies this particular error.
		* @param {Object=} details Any relevant arguments
		* that will help developers identify issues should
		* be added as a key on the context object.
		*/
		constructor(errorCode, details) {
			const message = messageGenerator(errorCode, details);
			super(message);
			this.name = errorCode;
			this.details = details;
		}
	};
	//#endregion
	//#region node_modules/.pnpm/workbox-range-requests@7.4.1/node_modules/workbox-range-requests/_version.js
	try {
		self["workbox:range-requests:7.4.0"] && _();
	} catch (e) {}
	//#endregion
	//#region node_modules/.pnpm/workbox-range-requests@7.4.1/node_modules/workbox-range-requests/utils/calculateEffectiveBoundaries.js
	/**
	* @param {Blob} blob A source blob.
	* @param {number} [start] The offset to use as the start of the
	* slice.
	* @param {number} [end] The offset to use as the end of the slice.
	* @return {Object} An object with `start` and `end` properties, reflecting
	* the effective boundaries to use given the size of the blob.
	*
	* @private
	*/
	function calculateEffectiveBoundaries(blob, start, end) {
		const blobSize = blob.size;
		if (end && end > blobSize || start && start < 0) throw new WorkboxError("range-not-satisfiable", {
			size: blobSize,
			end,
			start
		});
		let effectiveStart;
		let effectiveEnd;
		if (start !== void 0 && end !== void 0) {
			effectiveStart = start;
			effectiveEnd = end + 1;
		} else if (start !== void 0 && end === void 0) {
			effectiveStart = start;
			effectiveEnd = blobSize;
		} else if (end !== void 0 && start === void 0) {
			effectiveStart = blobSize - end;
			effectiveEnd = blobSize;
		}
		return {
			start: effectiveStart,
			end: effectiveEnd
		};
	}
	//#endregion
	//#region node_modules/.pnpm/workbox-range-requests@7.4.1/node_modules/workbox-range-requests/utils/parseRangeHeader.js
	/**
	* @param {string} rangeHeader A Range: header value.
	* @return {Object} An object with `start` and `end` properties, reflecting
	* the parsed value of the Range: header. If either the `start` or `end` are
	* omitted, then `null` will be returned.
	*
	* @private
	*/
	function parseRangeHeader(rangeHeader) {
		const normalizedRangeHeader = rangeHeader.trim().toLowerCase();
		if (!normalizedRangeHeader.startsWith("bytes=")) throw new WorkboxError("unit-must-be-bytes", { normalizedRangeHeader });
		if (normalizedRangeHeader.includes(",")) throw new WorkboxError("single-range-only", { normalizedRangeHeader });
		const rangeParts = /(\d*)-(\d*)/.exec(normalizedRangeHeader);
		if (!rangeParts || !(rangeParts[1] || rangeParts[2])) throw new WorkboxError("invalid-range-values", { normalizedRangeHeader });
		return {
			start: rangeParts[1] === "" ? void 0 : Number(rangeParts[1]),
			end: rangeParts[2] === "" ? void 0 : Number(rangeParts[2])
		};
	}
	//#endregion
	//#region node_modules/.pnpm/workbox-range-requests@7.4.1/node_modules/workbox-range-requests/createPartialResponse.js
	/**
	* Given a `Request` and `Response` objects as input, this will return a
	* promise for a new `Response`.
	*
	* If the original `Response` already contains partial content (i.e. it has
	* a status of 206), then this assumes it already fulfills the `Range:`
	* requirements, and will return it as-is.
	*
	* @param {Request} request A request, which should contain a Range:
	* header.
	* @param {Response} originalResponse A response.
	* @return {Promise<Response>} Either a `206 Partial Content` response, with
	* the response body set to the slice of content specified by the request's
	* `Range:` header, or a `416 Range Not Satisfiable` response if the
	* conditions of the `Range:` header can't be met.
	*
	* @memberof workbox-range-requests
	*/
	async function createPartialResponse(request, originalResponse) {
		try {
			if (originalResponse.status === 206) return originalResponse;
			const rangeHeader = request.headers.get("range");
			if (!rangeHeader) throw new WorkboxError("no-range-header");
			const boundaries = parseRangeHeader(rangeHeader);
			const originalBlob = await originalResponse.blob();
			const effectiveBoundaries = calculateEffectiveBoundaries(originalBlob, boundaries.start, boundaries.end);
			const slicedBlob = originalBlob.slice(effectiveBoundaries.start, effectiveBoundaries.end);
			const slicedBlobSize = slicedBlob.size;
			const slicedResponse = new Response(slicedBlob, {
				status: 206,
				statusText: "Partial Content",
				headers: originalResponse.headers
			});
			slicedResponse.headers.set("Content-Length", String(slicedBlobSize));
			slicedResponse.headers.set("Content-Range", `bytes ${effectiveBoundaries.start}-${effectiveBoundaries.end - 1}/${originalBlob.size}`);
			return slicedResponse;
		} catch (error) {
			return new Response("", {
				status: 416,
				statusText: "Range Not Satisfiable"
			});
		}
	}
	//#endregion
	//#region src/apps/slides/utils/slidesCaches.js
	var MEDIA_CACHE_NAME = "slides-media";
	var API_CACHE_NAME = "slides-api";
	var ASSETS_CACHE_NAME = "slides-assets";
	var SHELL_CACHE_NAME = "slides-shell";
	var PINNED_CACHE_NAME = "slides-pinned";
	var GUEST_HEADER = "x-suite-guest";
	var isMedia = (url) => url.pathname.startsWith("/api/method/suite.slides.api.file.get_media_file") || url.pathname.startsWith("/private/files/") && url.searchParams.has("slides_media");
	var isAPI = (url) => url.pathname.startsWith("/api/method/suite.slides.");
	var isPresentationDoc = (url) => url.pathname === "/api/method/frappe.client.get" && url.searchParams.get("doctype") === "Presentation";
	var isBundleAsset = (url) => url.pathname.startsWith("/assets/suite/frontend/assets/") && !url.pathname.endsWith(".map");
	var isSlidesStatic = (url) => url.pathname.startsWith("/assets/suite/slides/");
	var isSlidesPath = (pathname) => pathname === "/slides" || pathname.startsWith("/slides/");
	var isFromSlidesPage = (request) => {
		if (!request.referrer) return false;
		return isSlidesPath(new URL(request.referrer).pathname);
	};
	var isSlidesClient = (request, clientState) => {
		if (clientState === "entered") return true;
		return isFromSlidesPage(request) && clientState !== "left";
	};
	var isShell = (request, url) => isSlidesPath(url.pathname) && (request.mode === "navigate" || request.headers.get("x-slides-pin") === "shell");
	var getRequestType = (request, clientState) => {
		const url = new URL(request.url);
		if (isShell(request, url)) return "shell";
		if (isMedia(url)) return "media";
		if (isSlidesStatic(url)) return "asset";
		if (!isSlidesClient(request, clientState)) return "other";
		if (isAPI(url) || isPresentationDoc(url)) return "api";
		if (isBundleAsset(url)) return "asset";
		return "other";
	};
	var isMediaContentType = (response) => {
		const contentType = response.headers.get("Content-Type") || "";
		return ["image/", "video/"].some((ct) => contentType.startsWith(ct));
	};
	var isCacheable = (type, response) => {
		const contentType = response.headers.get("Content-Type") || "";
		if (type === "media") return isMediaContentType(response);
		if (type === "asset") return !response.redirected && !contentType.startsWith("text/html");
		if (type === "shell") return !response.redirected && contentType.startsWith("text/html") && !response.headers.has(GUEST_HEADER);
		return !response.redirected && contentType.includes("application/json");
	};
	//#endregion
	//#region src/apps/slides/utils/canonicalMediaKey.ts
	var parseUrl = (url) => {
		try {
			return new URL(url, "https://slides.invalid");
		} catch {
			return null;
		}
	};
	var canonicalMediaKey = (url) => {
		if (!url) return null;
		const parsed = parseUrl(url);
		if (!parsed) return null;
		if (parsed.pathname === "/api/method/suite.slides.api.file.get_media_file") return canonicalMediaKey(parsed.searchParams.get("src"));
		if (parsed.pathname.startsWith("/files/")) return `/private${parsed.pathname}`;
		if (parsed.pathname.startsWith("/private/files/")) return parsed.pathname;
		return null;
	};
	//#endregion
	//#region src/apps/slides/service-worker.js
	var SHELL_CACHE_KEY = "/slides";
	var DAY = 864e5;
	var CACHE_MAX_AGE = {
		[MEDIA_CACHE_NAME]: DAY,
		[ASSETS_CACHE_NAME]: 30 * DAY
	};
	self.addEventListener("install", () => {
		self.skipWaiting();
	});
	var openCache = (name) => caches.open(name).catch(() => null);
	var matchCache = (cache, request) => cache.match(request).catch(() => null);
	var cleanupOldCacheEntry = async (cache, request, response, maxAge) => {
		const now = Date.now();
		const cachedTimeHeader = response.headers.get("x-cached-time");
		if (!cachedTimeHeader) return;
		const cachedTime = parseInt(cachedTimeHeader, 10);
		if (isNaN(cachedTime)) return;
		if (now - cachedTime > maxAge) await cache.delete(request);
	};
	var cleanupOldCacheEntries = async (name, maxAge) => {
		const cache = await openCache(name);
		if (!cache) return;
		for (const request of await cache.keys()) {
			const response = await matchCache(cache, request);
			if (!response) continue;
			await cleanupOldCacheEntry(cache, request, response, maxAge);
		}
	};
	var handleSWActivate = async () => {
		await self.clients.claim();
		await Promise.all(Object.entries(CACHE_MAX_AGE).map(([name, maxAge]) => cleanupOldCacheEntries(name, maxAge).catch(() => {})));
	};
	self.addEventListener("activate", (event) => {
		event.waitUntil(handleSWActivate());
	});
	var getModifiedResponse = (response, type) => {
		const responseToCache = response.clone();
		const headers = new Headers(responseToCache.headers);
		headers.set("x-cached-time", Date.now().toString());
		if (type === "shell") headers.delete("Vary");
		return new Response(responseToCache.body, {
			status: responseToCache.status,
			statusText: responseToCache.statusText,
			headers
		});
	};
	var slidesClientState = /* @__PURE__ */ new Map();
	var forgetClosedClients = async () => {
		const clients = await self.clients.matchAll({ type: "window" });
		const open = new Set(clients.map((client) => client.id));
		for (const clientId of slidesClientState.keys()) if (!open.has(clientId)) slidesClientState.delete(clientId);
	};
	self.addEventListener("message", (event) => {
		const clientId = event.source?.id;
		if (!clientId) return;
		if (event.data === "slides-entered") slidesClientState.set(clientId, "entered");
		if (event.data === "slides-left") slidesClientState.set(clientId, "left");
		event.ports[0]?.postMessage(true);
		event.waitUntil(forgetClosedClients().catch(() => {}));
	});
	var addCacheEntry = async (type, cache, request, response) => {
		if (!isCacheable(type, response)) return;
		const modifiedResponse = getModifiedResponse(response, type);
		const key = type === "shell" ? SHELL_CACHE_KEY : request;
		await cache.put(key, modifiedResponse);
	};
	var fetchAndCache = async (event, type, cache) => {
		const response = await fetch(event.request);
		if (response.ok && response.status === 200) {
			const written = addCacheEntry(type, cache, event.request, response).catch((err) => {
				console.warn("Slides SW cache write failed:", err);
			});
			event.waitUntil(written);
		}
		return response;
	};
	var networkFirst = async (event, type, cache, key = event.request) => {
		const network = fetchAndCache(event, type, cache);
		try {
			return await network;
		} catch {}
		const cached = await matchCache(cache, key);
		if (!cached) return network;
		return cached;
	};
	var rangeFromCache = async (event, cached) => {
		const partial = await createPartialResponse(event.request, cached);
		if (partial.status === 416) return fetch(event.request);
		return partial;
	};
	var respondFromCache = (event, cached) => event.request.headers.has("range") ? rangeFromCache(event, cached) : cached;
	var staleWhileRevalidate = async (event, cache) => {
		const cached = await matchCache(cache, event.request);
		const network = fetchAndCache(event, "asset", cache);
		if (!cached) return network;
		event.waitUntil(network.catch(() => {}));
		return cached;
	};
	var cacheFirst = async (event, type, cache) => {
		const cached = await matchCache(cache, event.request);
		if (cached) return respondFromCache(event, cached);
		return fetchAndCache(event, type, cache);
	};
	var matchPinned = (request) => {
		const key = canonicalMediaKey(request.url);
		if (!key) return null;
		return caches.match(key, { cacheName: PINNED_CACHE_NAME }).catch(() => null);
	};
	var getPinnedResponse = async (event) => {
		const pinned = await matchPinned(event.request);
		return pinned ? respondFromCache(event, pinned) : null;
	};
	var getMediaResponse = async (event) => {
		if (event.request.headers.has("x-slides-pin")) return fetch(event.request);
		const pinned = await getPinnedResponse(event);
		if (pinned) return pinned;
		const cache = await openCache(MEDIA_CACHE_NAME);
		return cache ? cacheFirst(event, "media", cache) : fetch(event.request);
	};
	var getAssetResponse = async (event, url) => {
		const cache = await openCache(ASSETS_CACHE_NAME);
		if (!cache) return fetch(event.request);
		if (isBundleAsset(url)) return cacheFirst(event, "asset", cache);
		return staleWhileRevalidate(event, cache);
	};
	var getShellResponse = async (event) => {
		const cache = await openCache(SHELL_CACHE_NAME);
		if (!cache) return fetch(event.request);
		return networkFirst(event, "shell", cache, SHELL_CACHE_KEY);
	};
	var getResponseForRequest = async (event, type, url) => {
		if (type === "media") return getMediaResponse(event);
		if (type === "asset") return getAssetResponse(event, url);
		if (type === "shell") return getShellResponse(event);
		const cache = await openCache(API_CACHE_NAME);
		if (!cache) return fetch(event.request);
		return networkFirst(event, "api", cache);
	};
	self.addEventListener("fetch", (event) => {
		const request = event.request;
		const url = new URL(request.url);
		if (request.method !== "GET" || url.origin !== self.location.origin) return;
		const requestType = getRequestType(request, slidesClientState.get(event.clientId));
		if (requestType === "other") return;
		event.respondWith(getResponseForRequest(event, requestType, url));
	});
	//#endregion
})();
