import { ref, watch } from 'vue'

type Origin = {
	x: number
	y: number
}

type Transform = {
	origin: Origin
	scale: number
	translation: {
		x: number
		y: number
	}
}

export const usePanAndZoom = () => {
	const targetElement = ref<HTMLElement | null>(null)
	const containerElement = ref<HTMLElement | null>(null)
	const allowPanAndZoom = ref()

	const SCALE_SPEED = 0.5
	const TRANSLATE_SPEED = 0.5

	let origin: Origin, transformObj: Transform | null

	let initialX: number, initialY: number
	let initialMatrix = new DOMMatrix()
	let gestureMatrix = new DOMMatrix()

	let wheelTimeout: ReturnType<typeof setTimeout>

	const transform = ref('')
	const transformOrigin = ref('0 0')

	const setOrigin = () => {
		if (!transformObj) return
		// origin is the midpoint of the initial touch points
		origin = {
			x: transformObj.origin.x - initialX,
			y: transformObj.origin.y - initialY,
		}
	}

	const startGesture = () => {
		transform.value = ''
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
		if (!transformObj) return
		// previous scale for transformation matrix is length of hypotenuse of x and y components
		let scale = Math.hypot(initialMatrix.a, initialMatrix.b)
		let currentScale = transformObj.scale * scale

		// limit scale between 0.5 - 2
		if (currentScale > 5 || currentScale < 0.5) {
			transformObj.scale = Math.max(0.5, Math.min(5, currentScale)) / scale
		}
	}

	const limitTranslation = () => {
		if (!transformObj) return
		let nextX = transformObj.translation.x + initialMatrix.e
		let nextY = transformObj.translation.y + initialMatrix.f

		let scale = Math.hypot(initialMatrix.a, initialMatrix.b)

		// if target goes out of bounds from top or bottom
		// reduce the translation on Y axis
		let ylimit = scale < 1 ? 500 * scale : 500
		if (nextY > ylimit) transformObj.translation.y = ylimit - initialMatrix.f
		else if (nextY < -ylimit) transformObj.translation.y = -ylimit - initialMatrix.f

		// if target goes out of bounds from top or bottom
		// reduce the translation on X axis
		let xlimit = scale < 1 ? 800 * scale : 800
		if (nextX > xlimit) transformObj.translation.x = xlimit - initialMatrix.e
		else if (nextX < -xlimit) transformObj.translation.x = -xlimit - initialMatrix.e
	}

	const setGestureMatrix = () => {
		if (!transformObj) return
		let matrix = new DOMMatrix()
			.translate(origin.x, origin.y)
			.translate(transformObj.translation.x, transformObj.translation.y)
			.scale(transformObj.scale || 1)
			.translate(-origin.x, -origin.y)

		gestureMatrix = matrix.multiply(initialMatrix)
	}

	const applyMatrix = () => {
		transform.value = gestureMatrix.toString()
	}

	const setZoomTransform = (e: WheelEvent) => {
		if (!transformObj) return
		let dy = e.deltaY * SCALE_SPEED
		let factor = e.deltaY <= 0 ? 1 - dy / 100 : 1 / (1 + dy / 100)
		transformObj = {
			origin: { x: e.clientX, y: e.clientY },
			scale: transformObj.scale * factor,
			translation: transformObj.translation,
		}
	}

	const setPanTransform = (e: WheelEvent) => {
		if (!transformObj) return
		let dx = e.deltaX * TRANSLATE_SPEED
		let dy = e.deltaY * TRANSLATE_SPEED
		transformObj = {
			origin: { x: e.clientX, y: e.clientY },
			scale: transformObj.scale,
			translation: {
				x: transformObj.translation.x - dx,
				y: transformObj.translation.y - dy,
			},
		}
	}

	const handlePanAndZoom = (e: WheelEvent) => {
		e.preventDefault()
		if (e.composedPath().some((el) => (el as HTMLElement).id === 'slide-navigation-panel')) return

		// initialize the transformObj
		if (!transformObj) {
			transformObj = {
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

		// incrementally update the transformObj
		updateGesture()

		if (wheelTimeout) window.clearTimeout(wheelTimeout)
		wheelTimeout = setTimeout(() => {
			// apply the final transformation
			endGesture()
			transformObj = null
		}, 200)
	}

	const addPanAndZoom = () => {
		if (!containerElement.value || !targetElement.value) return
		initialMatrix = new DOMMatrix()
		gestureMatrix = new DOMMatrix()
		let rect = targetElement.value.getBoundingClientRect()
		initialX = rect.x
		initialY = rect.y
		containerElement.value.addEventListener('wheel', handlePanAndZoom, {
			passive: false,
		})
	}

	const removePanAndZoom = () => {
		if (!containerElement.value) return
		containerElement.value.removeEventListener('wheel', handlePanAndZoom)
	}

	watch(
		() => allowPanAndZoom.value,
		(value: boolean) => {
			value ? addPanAndZoom() : removePanAndZoom()
		},
	)

	return { transform, transformOrigin, allowPanAndZoom, targetElement, containerElement }
}
