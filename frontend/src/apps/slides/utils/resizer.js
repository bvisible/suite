import { ref } from 'vue'

export const useResizer = () => {
	const isResizing = ref(false)
	const currentResizer = ref(null)

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
			case 'resizer-left':
				diffLeft = -diffX
				break
			case 'resizer-top-right':
				diffX = -diffX
				diffTop = -diffX
				break
			case 'resizer-bottom-left':
				diffLeft = -diffX
				break
			case 'resizer-top-left':
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

	return { dimensionDelta, currentResizer, startResize }
}
