import { ref } from 'vue'

export const useDragAndDrop = () => {
	const isDragging = ref(false)

	const prevX = ref(0)
	const prevY = ref(0)

	const positionDelta = ref({ x: 0, y: 0 })

	const startDragging = (e) => {
		e.preventDefault()
		e.stopPropagation()

		isDragging.value = true

		prevX.value = e.clientX
		prevY.value = e.clientY

		window.addEventListener('mousemove', drag)
		window.addEventListener('mouseup', stopDragging)
	}

	const drag = (e) => {
		e.preventDefault()

		if (isDragging.value) {
			const dx = e.clientX - prevX.value
			const dy = e.clientY - prevY.value

			positionDelta.value = {
				x: dx,
				y: dy,
			}

			prevX.value = e.clientX
			prevY.value = e.clientY
		}
	}

	const stopDragging = (e) => {
		e.preventDefault()
		e.stopPropagation()

		isDragging.value = false

		positionDelta.value = { x: 0, y: 0 }

		window.removeEventListener('mousemove', drag)
		window.removeEventListener('mouseup', stopDragging)
	}

	return { isDragging, positionDelta, startDragging }
}
