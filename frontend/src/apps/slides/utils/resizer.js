import { ref, computed } from 'vue'

export const useResizer = (elementType) => {
	const isResizing = ref(false)
	const currentResizer = ref(null)

	const cursorMap = {
		'top-left': 'nwse-resize',
		'top-right': 'nesw-resize',
		'bottom-left': 'nesw-resize',
		'bottom-right': 'nwse-resize',
		left: 'ew-resize',
		right: 'ew-resize',
	}

	const resizeCursor = computed(() => cursorMap[currentResizer.value] ?? 'default')

	const isResizeHandleVisible = (resizer) => {
		if (!currentResizer.value) return true
		return currentResizer.value === resizer
	}

	const resizeHandles = computed(() => {
		const directions =
			elementType === 'text'
				? ['left', 'right']
				: ['top-left', 'top-right', 'bottom-left', 'bottom-right']

		return directions.map((direction) => ({
			direction,
			isVisible: isResizeHandleVisible(direction),
		}))
	})

	let prevX = 0
	let prevY = 0

	const dimensionDelta = ref({
		width: 0,
		height: 0,
		left: 0,
		top: 0,
	})

	const startResize = (e, resizer) => {
		e.preventDefault()
		e.stopImmediatePropagation()

		currentResizer.value = resizer
		isResizing.value = true

		prevX = e.clientX
		prevY = e.clientY

		window.addEventListener('mousemove', resize)
		window.addEventListener('mouseup', stopResize, { once: true })
	}

	const resize = (e) => {
		e.preventDefault()
		e.stopImmediatePropagation()

		let diffX = prevX - e.clientX
		let diffY = prevY - e.clientY

		let diffLeft = 0
		let diffTop = 0

		if (!diffX) return

		switch (currentResizer.value) {
			case 'left':
				diffLeft = -diffX
				break
			case 'top-right':
				diffX = -diffX
				diffTop = -diffX
				break
			case 'bottom-left':
				diffLeft = -diffX
				break
			case 'top-left':
				diffLeft = -diffX
				diffTop = -diffX
				break
			default:
				diffX = -diffX
				break
		}

		dimensionDelta.value = {
			width: diffX,
			left: diffLeft,
			top: diffTop,
		}

		prevX = e.clientX
		prevY = e.clientY
	}

	const stopResize = (e) => {
		e.preventDefault()
		e.stopImmediatePropagation()

		currentResizer.value = null
		isResizing.value = false

		window.removeEventListener('mousemove', resize)
		window.removeEventListener('mouseup', stopResize)
	}

	return { dimensionDelta, currentResizer, startResize, resizeHandles, resizeCursor }
}
