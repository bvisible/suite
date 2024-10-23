import { watch, ref, computed } from 'vue'

export const useResizer = (position, resizeDimensions) => {
	const resizeTarget = ref(null)
	const isResizing = ref(false)
	const currentResizer = ref(null)
	const resizeMode = ref(null)
	const resizeHandles = computed(() =>
		resizeMode.value == 'both'
			? ['top-left', 'top-right', 'bottom-left', 'bottom-right']
			: ['left', 'right'],
	)

	let originalWidth = null
	let originalHeight = null

	let originalBottom = null
	let originalLeft = null

	let prevX = 0
	let prevY = 0

	const startResize = (e) => {
		e.preventDefault()
		e.stopImmediatePropagation()

		currentResizer.value = e.target.classList[1]
		isResizing.value = true

		prevX = e.clientX
		prevY = e.clientY

		let rect = resizeTarget.value.getBoundingClientRect()
		let container = resizeTarget.value.parentElement.getBoundingClientRect()

		originalWidth = rect.width
		originalHeight = rect.height

		originalBottom = rect.bottom - container.bottom
		originalLeft = rect.left - container.left

		window.addEventListener('mousemove', resize)
		window.addEventListener('mouseup', stopResize, { once: true })
	}

	const resize = (e) => {
		e.preventDefault()
		e.stopImmediatePropagation()

		const rect = resizeTarget.value.getBoundingClientRect()
		const container = resizeTarget.value.parentElement.getBoundingClientRect()

		let newLeft = 0
		let newTop = 0

		let newWidth = 0
		let newHeight = 0

		let diffX = prevX - e.clientX
		let diffY = prevY - e.clientY

		if (!diffX) return

		switch (currentResizer.value) {
			case 'resizer-left':
				newWidth = rect.width + diffX
				newLeft = originalLeft + originalWidth - newWidth
				newTop = position.value.top
				break
			case 'resizer-top-right':
				newWidth = rect.width - diffX
				newHeight = (newWidth * originalHeight) / originalWidth
				newTop = originalBottom - newHeight
				newLeft = position.value.left
				break
			case 'resizer-bottom-left':
				newWidth = rect.width + diffX
				newLeft = originalLeft + originalWidth - newWidth
				newTop = position.value.top
				break
			case 'resizer-top-left':
				newWidth = rect.width + diffX
				newHeight = (newWidth * originalHeight) / originalWidth
				newLeft = originalLeft + originalWidth - newWidth
				newTop = originalBottom - newHeight
				break
			default:
				newWidth = rect.width - diffX
				newLeft = position.value.left
				newTop = position.value.top
				break
		}

		resizeDimensions.value = { width: newWidth }
		position.value = { left: newLeft, top: newTop }

		prevX = e.clientX
		prevY = e.clientY
	}

	const stopResize = (e) => {
		e.preventDefault()
		e.stopImmediatePropagation()
		window.removeEventListener('mousemove', resize)
		window.removeEventListener('mouseup', stopResize)
	}

	watch(
		() => resizeTarget.value,
		(val, oldVal) => {
			if (oldVal) {
				const resizers = oldVal.querySelectorAll('div.resizer-both, div.resizer-width')
				resizers.forEach((resizer) => {
					oldVal.removeChild(resizer)
				})
			}
			if (val) {
				resizeHandles.value.forEach((handle) => {
					const resizer = document.createElement('div')
					resizer.classList.add(`resizer-${resizeMode.value}`, `resizer-${handle}`)
					resizer.addEventListener('mousedown', startResize)
					val.appendChild(resizer)
				})
			}
		},
		{ immediate: true },
	)

	return { isResizing, resizeTarget, resizeMode }
}
