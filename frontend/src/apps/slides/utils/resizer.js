import { watch, ref } from 'vue'

export const useResizer = (position, resizeDimensions) => {
	const resizeTarget = ref(null)
	const isResizing = ref(false)
	const currentResizer = ref(null)

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

		let newTop = 0
		let newLeft = 0
		let newWidth = 0
		let newHeight = 0

		if (currentResizer.value == 'resizer-left') {
			if (e.offsetX == 0) return
			newWidth = rect.width + (prevX - e.clientX)
			newLeft = originalLeft + originalWidth - newWidth
			resizeDimensions.value = { ...resizeDimensions.value, width: newWidth }
			position.value = { ...position.value, left: newLeft }
		} else if (currentResizer.value == 'resizer-right') {
			newWidth = rect.width - (prevX - e.clientX)
			resizeDimensions.value = { ...resizeDimensions.value, width: newWidth }
		} else if (currentResizer.value == 'resizer-bottom-right') {
			newWidth = rect.width - (prevX - e.clientX)
			resizeDimensions.value = { width: newWidth }
		} else if (currentResizer.value == 'resizer-top-right') {
			let diffX = prevX - e.clientX
			let diffY = prevY - e.clientY
			if (diffX && diffY) {
				newWidth = rect.width - diffX
				newHeight = (newWidth * originalHeight) / originalWidth
				newTop = originalBottom - newHeight

				resizeDimensions.value = { ...resizeDimensions.value, width: newWidth }
				position.value = { ...position.value, top: newTop }
			}
		} else if (currentResizer.value == 'resizer-bottom-left') {
			newWidth = rect.width + (prevX - e.clientX)
			newLeft = originalLeft + originalWidth - newWidth

			resizeDimensions.value = { ...resizeDimensions.value, width: newWidth }
			position.value = { ...position.value, left: newLeft }
		} else if (currentResizer.value == 'resizer-top-left') {
			let diffX = prevX - e.clientX
			let diffY = prevY - e.clientY
			if (diffX && diffY) {
				newWidth = rect.width + diffX
				newHeight = (newWidth * originalHeight) / originalWidth
				newTop = originalBottom - newHeight
				newLeft = originalLeft + originalWidth - newWidth

				resizeDimensions.value = { ...resizeDimensions.value, width: newWidth }
				position.value = { left: newLeft, top: newTop }
			}
		}

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
				const resizers = oldVal.querySelectorAll('div.resizer-horizontal, div.resizer')
				resizers.forEach((resizer) => {
					oldVal.removeChild(resizer)
				})
			}
			if (val) {
				let resizerType = val.classList.contains('textElement')
					? 'resizer-horizontal'
					: 'resizer'
				const resizeHandles =
					resizerType == 'resizer-horizontal'
						? ['left', 'right']
						: ['top-left', 'top-right', 'bottom-left', 'bottom-right']
				resizeHandles.forEach((handle) => {
					const resizer = document.createElement('div')
					resizer.classList.add(resizerType, `resizer-${handle}`)
					resizer.addEventListener('mousedown', startResize)
					val.appendChild(resizer)
				})
			}
		},
		{ immediate: true },
	)

	return { isResizing, resizeTarget }
}
