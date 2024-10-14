import { watch, ref } from 'vue'

export const useResizer = () => {
	const resizeTarget = ref(null)
	const isResizing = ref(false)
	const currentResizer = ref(null)
	const resizeDimensions = ref({
		left: 0,
		top: 0,
		width: 0,
		height: 0,
	})

	let originalX = null
	let originalY = null
	let originalWidth = null
	let originalHeight = null
	let originalMouseX = 0
	let originalMouseY = 0

	const startResize = (e) => {
		e.preventDefault()
		e.stopImmediatePropagation()
		isResizing.value = true
		currentResizer.value = e.target.classList[1]

		originalMouseX = e.pageX
		originalMouseY = e.pageY

		originalWidth = parseInt(resizeDimensions.value.width)
		originalHeight = parseInt(resizeDimensions.value.height)
		originalX = parseInt(resizeDimensions.value.left)
		originalY = parseInt(resizeDimensions.value.top)

		window.addEventListener('mousemove', resize)
		window.addEventListener('mouseup', stopResize, { once: true })
	}

	const resize = (e) => {
		e.preventDefault()
		e.stopImmediatePropagation()
		let newLeft = 0
		let newWidth = 0

		if (currentResizer.value == 'resizer-left') {
			if (e.offsetX == 0) return
			newLeft = originalX + (e.pageX - originalMouseX)
			newWidth = originalWidth - (e.pageX - originalMouseX)
			if (newWidth > 30)
				resizeDimensions.value = {
					...resizeDimensions.value,
					left: newLeft,
					width: newWidth,
				}
		} else if (currentResizer.value == 'resizer-right') {
			newWidth = originalWidth + (e.pageX - originalMouseX)
			if (newWidth > 30)
				resizeDimensions.value = { ...resizeDimensions.value, width: newWidth }
		}
	}

	const stopResize = (e) => {
		e.preventDefault()
		e.stopImmediatePropagation()
		window.removeEventListener('mousemove', resize)
	}

	watch(
		() => resizeTarget.value,
		(val, oldVal) => {
			if (oldVal) {
				const resizers = oldVal.querySelectorAll('.resizer')
				resizers.forEach((resizer) => {
					oldVal.removeChild(resizer)
				})
			}
			if (val) {
				const resizeHandles = ['left', 'right']
				resizeHandles.forEach((handle) => {
					const resizer = document.createElement('div')
					resizer.classList.add('resizer', `resizer-${handle}`)
					resizer.addEventListener('mousedown', startResize)
					val.appendChild(resizer)
				})
			}
		},
		{ immediate: true },
	)

	return { resizeTarget, resizeDimensions }
}
