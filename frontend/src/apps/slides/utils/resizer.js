import { watch, ref, computed, reactive } from 'vue'
import { slide, slideBounds } from '../stores/slide'

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

	const resizeDiffs = ref({
		width: 0,
		height: 0,
		left: 0,
		top: 0,
	})

	const startResize = (e) => {
		e.preventDefault()
		e.stopImmediatePropagation()

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
			// case 'resizer-top-right':
			//     newWidth = rect.width - diffX
			//     activeBounds.width = newWidth
			//     activeBounds.top += diffX
			//     break
			// case 'resizer-bottom-left':
			//     newWidth = rect.width + diffX
			//     activeBounds.width = newWidth
			//     activeBounds.left -= diffX
			//     break
			// case 'resizer-top-left':
			//     newWidth = rect.width + diffX
			//     activeBounds.width = newWidth
			//     activeBounds.left -= diffX
			//     activeBounds.top -= (diffX * originalHeight) / originalWidth
			//     break
			default:
				diffX = -diffX
				break
		}

		resizeDiffs.value = {
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

		window.removeEventListener('mousemove', resize)
		window.removeEventListener('mouseup', stopResize)
	}

	const resizeToFitContent = (e) => {
		// create range of the text node within TextElement
		const range = document.createRange()
		const textNode = resizeTarget.value.firstChild
		range.selectNodeContents(textNode)

		// find out width of text content
		const textWidth = range.getBoundingClientRect().width

		// auto resize width of TextElement to fit content with some padding
		// dimensions.value = { width: textWidth + 10 }
	}

	const addResizers = (e, resizeMode) => {
		const el = e.target
		let resizeHandles = []
		if (resizeMode == 'width') resizeHandles = ['left', 'right']

		resizeHandles.forEach((handle) => {
			const resizer = document.createElement('div')
			resizer.classList.add(`resizer-${resizeMode}`, `resizer-${handle}`)

			// add double click event to fit content based on type of element
			if (resizeMode == 'width') {
				resizer.addEventListener('dblclick', resizeToFitContent)
			}
			resizer.addEventListener('mousedown', startResize)

			el.appendChild(resizer)
		})
	}

	const removeResizers = (el) => {
		const resizers = el.querySelectorAll('div.resizer-both, div.resizer-width')
		resizers.forEach((resizer) => {
			el.removeChild(resizer)
		})
	}

	return { isResizing, resizeDiffs, addResizers }
}
