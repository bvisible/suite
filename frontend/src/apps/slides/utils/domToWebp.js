import { createContext, domToWebp } from 'modern-screenshot'

const CAPTURE_WIDTH = 960
const CAPTURE_HEIGHT = 540
const CAPTURE_TIMEOUT = 5000

const waitForFonts = async () => {
	if (!document.fonts?.ready) return
	await Promise.race([document.fonts.ready, wait(CAPTURE_TIMEOUT)])
}

const waitForImages = async (node) => {
	const images = Array.from(node.querySelectorAll('img'))
	await Promise.all(images.map((image) => waitForImage(image)))
}

const waitForImage = (image) => {
	if (image.complete) return Promise.resolve()

	return new Promise((resolve) => {
		const cleanup = () => {
			image.removeEventListener('load', cleanup)
			image.removeEventListener('error', cleanup)
			clearTimeout(timeout)
			resolve()
		}
		const timeout = setTimeout(cleanup, CAPTURE_TIMEOUT)
		image.addEventListener('load', cleanup, { once: true })
		image.addEventListener('error', cleanup, { once: true })
	})
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

let _captureContext = null

const getContext = async (node, options) => {
	if (!_captureContext) {
		// so fonts are not loaded again and again
		_captureContext = await createContext(node, { ...options, autoDestruct: false })
	} else {
		_captureContext.node = node
		// Reset per-capture font state so only fonts used by this node are embedded.
		_captureContext.fontFamilies = new Map()
		_captureContext.fontCssTexts = new Map()
		// shadowRoots accumulates across captures and is not auto-reset by
		// autoDestruct:false — clear it to avoid stale references.
		_captureContext.shadowRoots = []
		// tasks should be empty after a successful capture (all popped), but
		// reset defensively in case a previous capture failed mid-way.
		_captureContext.tasks = []
	}
	return _captureContext
}

export const captureDOM = async (node) => {
	await waitForFonts()
	await waitForImages(node)

	const options = {
		width: CAPTURE_WIDTH,
		height: CAPTURE_HEIGHT,
		scale: 1,
		backgroundColor: '#ffffff',
		timeout: CAPTURE_TIMEOUT,
		quality: 0.86,
		type: 'image/webp',
	}

	const ctx = await getContext(node, options)
	const webp = await domToWebp(ctx)
	if (!webp?.startsWith('data:image/webp')) {
		throw new Error('Could not generate WebP thumbnail')
	}
	return webp
}
