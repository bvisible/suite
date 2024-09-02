// co-efficient for how sensitive the zoom is to the mouse wheel
const SCALE_SPEED = 0.5

// co-efficient for how sensitive the pan is to the mouse wheel
const TRANSLATE_SPEED = 0.5

let target, origin, transform
let initialTransform = new DOMMatrix()

const startPanOrZoom = () => {
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
	limitTranslation()
	let m = getMatrix(transform).multiply(initialTransform)
	target.style.transform = m
}

const endPanOrZoom = () => {
	limitScale()
	limitTranslation()
	initialTransform = getMatrix(transform).multiply(initialTransform)
	target.style.transform = initialTransform
}

const getMatrix = () => {
	return new DOMMatrix()
		.translate(origin.x, origin.y)
		.translate(transform.translation.x, transform.translation.y)
		.scale(transform.scale || 1)
		.translate(-origin.x, -origin.y)
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

const limitTranslation = () => {
	let nextX = transform.translation.x + initialTransform.e
	let nextY = transform.translation.y + initialTransform.f

	let scale = Math.hypot(initialTransform.a, initialTransform.b)

	// if target goes out of bounds from top or bottom
	// reduce the translation on Y axis
	let ylimit = scale < 1 ? 600 * scale : 600
	if (nextY > ylimit) transform.translation.y = ylimit - initialTransform.f
	else if (nextY < -ylimit) transform.translation.y = -ylimit - initialTransform.f

	// if target goes out of bounds from top or bottom
	// reduce the translation on X axis
	let xlimit = scale < 1 ? 1150 * scale : 1150
	if (nextX > xlimit) transform.translation.x = xlimit - initialTransform.e
	else if (nextX < -xlimit) transform.translation.x = -xlimit - initialTransform.e
}

const addPanAndZoom = (containerElement, targetElement) => {
	target = targetElement
	let wheelTimeout = null

	const handlePanAndZoom = (e) => {
		e.preventDefault()

		if (!transform) {
			transform = {
				origin: { x: e.clientX, y: e.clientY },
				scale: 1,
				translation: { x: 0, y: 0 },
			}
			startPanOrZoom()
		}

		if (e.ctrlKey) {
			let zoom_factor = e.deltaY <= 0 ? 1 - e.deltaY / 100 : 1 / (1 + e.deltaY / 100)
			transform = {
				origin: { x: e.clientX, y: e.clientY },
				scale: transform.scale * zoom_factor,
				translation: transform.translation,
			}
		} else {
			let dx = e.deltaX * TRANSLATE_SPEED
			let dy = e.deltaY * TRANSLATE_SPEED
			transform = {
				origin: { x: e.clientX, y: e.clientY },
				scale: transform.scale,
				translation: {
					x: transform.translation.x - dx,
					y: transform.translation.y - dy,
				},
			}
		}

		updateTransform()

		if (wheelTimeout) window.clearTimeout(wheelTimeout)
		wheelTimeout = setTimeout(() => {
			endPanOrZoom()
			transform = null
		}, 200)
	}

	containerElement.addEventListener('wheel', handlePanAndZoom, {
		passive: false,
	})
}

export { addPanAndZoom }
