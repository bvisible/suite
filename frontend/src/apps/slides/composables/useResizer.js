import { ref, computed } from 'vue'

export const useResizer = () => {
	const isResizing = ref(false)
	const currentResizer = ref(null)

	const cursorMap = {
		'top-left': 'nwse-resize',
		'top-right': 'nesw-resize',
		'bottom-left': 'nesw-resize',
		'bottom-right': 'nwse-resize',
		'text-left': 'ew-resize',
		'text-right': 'ew-resize',
		left: 'ew-resize',
		right: 'ew-resize',
		top: 'ns-resize',
		bottom: 'ns-resize',
	}

	const resizeCursor = computed(() => cursorMap[currentResizer.value] ?? 'default')

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
			case 'text-left':
				diffLeft = -diffX / 2
				break
			case 'text-right':
				diffLeft = -diffX / 2
				diffX = -diffX
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
			case 'left':
				diffLeft = -diffX
				diffY = 0
				break
			case 'bottom':
				diffY = -diffY
				diffX = 0
				break
			case 'top':
				diffTop = -diffY
				diffX = 0
				break
			case 'right':
				diffX = -diffX
				diffY = 0
				break
			default:
				diffX = -diffX
				break
		}

		requestAnimationFrame(() => {
			dimensionDelta.value = {
				height: diffY,
				width: diffX,
				left: diffLeft,
				top: diffTop,
			}
		})

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

	return { isResizing, dimensionDelta, currentResizer, startResize, resizeCursor }
}
