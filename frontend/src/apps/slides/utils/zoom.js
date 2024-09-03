// co-efficient for how sensitive the zoom is to the mouse wheel
const SCALE_SPEED = 0.5

// co-efficient for how sensitive the pan is to the mouse wheel
const TRANSLATE_SPEED = 0.5

let target, origin, transform

let initialMatrix = new DOMMatrix()
let gestureMatrix = new DOMMatrix()

let wheelTimeout = null

const setOrigin = () => {
	// origin is the midpoint of the initial touch points
	let targetRect = target.getBoundingClientRect()
	origin = {
		x: transform.origin.x - targetRect.x,
		y: transform.origin.y - targetRect.y,
	}
}

const startGesture = () => {
	setOrigin()
	setGestureMatrix()
	applyMatrix()
}

const updateGesture = () => {
	limitScale()
	limitTranslation()
	setGestureMatrix()
	applyMatrix()
}

const endGesture = () => {
	limitScale()
	limitTranslation()
	setGestureMatrix()
	// while ending transform, apply the final transformation matrix
	initialMatrix = gestureMatrix
	applyMatrix()
}

const limitScale = () => {
	// previous scale for transformation matrix is length of hypotenuse of x and y components
	let scale = Math.hypot(initialMatrix.a, initialMatrix.b)
	let currentScale = transform.scale * scale

	// limit scale between 0.5 - 2
	if (currentScale > 2 || currentScale < 0.5) {
		transform.scale = Math.max(0.5, Math.min(2, currentScale)) / scale
	}
}

const limitTranslation = () => {
	let nextX = transform.translation.x + initialMatrix.e
	let nextY = transform.translation.y + initialMatrix.f

	let scale = Math.hypot(initialMatrix.a, initialMatrix.b)

	// if target goes out of bounds from top or bottom
	// reduce the translation on Y axis
	let ylimit = scale < 1 ? 600 * scale : 600
	if (nextY > ylimit) transform.translation.y = ylimit - initialMatrix.f
	else if (nextY < -ylimit) transform.translation.y = -ylimit - initialMatrix.f

	// if target goes out of bounds from top or bottom
	// reduce the translation on X axis
	let xlimit = scale < 1 ? 1150 * scale : 1150
	if (nextX > xlimit) transform.translation.x = xlimit - initialMatrix.e
	else if (nextX < -xlimit) transform.translation.x = -xlimit - initialMatrix.e
}

const setGestureMatrix = () => {
	let matrix = new DOMMatrix()
		.translate(origin.x, origin.y)
		.translate(transform.translation.x, transform.translation.y)
		.scale(transform.scale || 1)
		.translate(-origin.x, -origin.y)

	gestureMatrix = matrix.multiply(initialMatrix)
}

const applyMatrix = () => {
	target.style.transform = gestureMatrix.toString()
}

const setZoomTransform = (e) => {
	let dy = e.deltaY * SCALE_SPEED
	let factor = e.deltaY <= 0 ? 1 - dy / 100 : 1 / (1 + dy / 100)
	transform = {
		origin: { x: e.clientX, y: e.clientY },
		scale: transform.scale * factor,
		translation: transform.translation,
	}
}

const setPanTransform = (e) => {
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

const handlePanAndZoom = (e) => {
	e.preventDefault()

	// initialize the transform object
	if (!transform) {
		transform = {
			origin: { x: e.clientX, y: e.clientY },
			scale: 1,
			translation: { x: 0, y: 0 },
		}
		startGesture()
	}

	if (e.ctrlKey) {
		setZoomTransform(e)
	} else {
		setPanTransform(e)
	}

	// incrementally update the transform object
	updateGesture(e)

	if (wheelTimeout) window.clearTimeout(wheelTimeout)
	wheelTimeout = setTimeout(() => {
		// apply the final transformation
		endGesture()
		transform = null
	}, 200)
}

const addPanAndZoom = (containerElement, targetElement) => {
	target = targetElement
	containerElement.addEventListener('wheel', handlePanAndZoom, {
		passive: false,
	})
}

export { addPanAndZoom }
