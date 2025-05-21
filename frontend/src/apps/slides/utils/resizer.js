import { ref } from 'vue'
import { slide } from '../stores/slide'

export const useResizer = () => {
	const resizeTarget = ref(null)
	const isResizing = ref(false)
	const currentResizer = ref(null)

	let originalWidth = null
	let originalHeight = null

	let originalBottom = null
	let originalLeft = null

	let prevX = 0
	let prevY = 0

	const dimensionDelta = ref({
		width: 0,
		height: 0,
		left: 0,
		top: 0,
	})

	const startResize = (e) => {
		e.preventDefault()
		e.stopImmediatePropagation()

		isResizing.value = true

		currentResizer.value = e.target.classList[1]
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
				diffTop = -diffX
				diffLeft = -diffX
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

		isResizing.value = false

		window.removeEventListener('mousemove', resize)
		window.removeEventListener('mouseup', stopResize)
	}

	const resizeToFitContent = (e) => {
		// create range of the text node within TextElement
		const range = document.createRange()
		const textNode = e.target.parentElement.firstChild
		const originalWidth = e.target.parentElement.offsetWidth
		range.selectNodeContents(textNode)

		// find out width of text content
		const textWidth = range.getBoundingClientRect().width
		// auto resize width of TextElement to fit content with some padding
		dimensionDelta.value = {
			width: textWidth - originalWidth + 5,
			left: 0,
			top: 0,
		}
	}

	const getResizeHandlers = (resizeMode) => {
		if (resizeMode == 'width') {
			return ['left', 'right']
		} else {
			return ['top-left', 'top-right', 'bottom-left', 'bottom-right']
		}
	}

	const createResizeHandle = (resizeMode, handle) => {
		const resizer = document.createElement('div')
		resizer.classList.add(`resizer-${resizeMode}`, `resizer-${handle}`)

		// add double click event to fit content based on type of element
		if (resizeMode == 'width') {
			resizer.addEventListener('dblclick', resizeToFitContent)
		}
		resizer.addEventListener('mousedown', startResize)

		resizeTarget.value.appendChild(resizer)
	}

	const addResizers = (resizeMode) => {
		const resizeHandles = getResizeHandlers(resizeMode)

		resizeHandles.forEach((handle) => createResizeHandle(resizeMode, handle))
	}

	const updateResizers = (target, resizeMode) => {
		removeResizers()

		if (!target) return

		resizeTarget.value = target

		addResizers(resizeMode)
	}

	const removeResizers = () => {
		if (!resizeTarget.value) return
		const resizers = resizeTarget.value.querySelectorAll('div.resizer-both, div.resizer-width')
		resizers.forEach((resizer) => {
			resizeTarget.value.removeChild(resizer)
		})
	}

	return { isResizing, dimensionDelta, updateResizers }
}
