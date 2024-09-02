// co-efficient for how sensitive the zoom is to the mouse wheel
const SCALE_SPEED = 0.5

let target, origin, transform
let initialTransform = new DOMMatrix()

const startZoom = () => {
	let targetRect = target.getBoundingClientRect()
	origin = {
		x: transform.origin.x - targetRect.x,
		y: transform.origin.y - targetRect.y,
	}
	let m = getMatrix(transform).multiply(initialTransform)
	target.style.transform = m
}

const updateTransform = () => {
	limitScale()
	let m = getMatrix(transform).multiply(initialTransform)
	target.style.transform = m
}

const endZoom = () => {
	limitScale()
	initialTransform = getMatrix(transform).multiply(initialTransform)
	target.style.transform = initialTransform
}

const getMatrix = () => {
	return new DOMMatrix().scale(transform.scale || 1)
}

const limitScale = () => {
	// previous scale for transformation matrix is length of hypotenuse of x and y components
	let scale = Math.hypot(initialTransform.a, initialTransform.b)
	let currentScale = transform.scale * scale

	// limit scale between 0.5 - 2
	if (currentScale > 2 || currentScale < 0.5) {
		transform.scale = Math.max(0.5, Math.min(2, currentScale)) / scale
	}
}

const setupZooming = (containerElement, targetElement) => {
	target = targetElement
	let wheelTimeout = null

	const handleZoom = (e) => {
		e.preventDefault()

		if (!transform) {
			transform = {
				origin: { x: e.clientX, y: e.clientY },
				scale: 1,
			}
			startZoom()
		}

		if (e.ctrlKey) {
			let dy = e.deltaY * SCALE_SPEED
			let zoom_factor = e.deltaY <= 0 ? 1 - dy / 100 : 1 / (1 + dy / 100)
			transform = {
				origin: { x: e.clientX, y: e.clientY },
				scale: transform.scale * zoom_factor,
			}
		}

		updateTransform()

		if (wheelTimeout) window.clearTimeout(wheelTimeout)
		wheelTimeout = setTimeout(() => {
			endZoom()
			transform = null
		}, 200)
	}

	containerElement.addEventListener('wheel', handleZoom, {
		passive: false,
	})
}

export { setupZooming }
