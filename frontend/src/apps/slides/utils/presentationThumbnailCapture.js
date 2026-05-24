import { domToWebp } from 'modern-screenshot'

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

export const capturePresentationThumbnail = async (node) => {
	await waitForFonts()
	await waitForImages(node)

	const options = {
		width: CAPTURE_WIDTH,
		height: CAPTURE_HEIGHT,
		scale: 1,
		backgroundColor: '#ffffff',
		timeout: CAPTURE_TIMEOUT,
	}

	const webp = await domToWebp(node, { ...options, quality: 0.86 })
	if (!webp?.startsWith('data:image/webp')) {
		throw new Error('Could not generate WebP thumbnail')
	}
	return webp
}
