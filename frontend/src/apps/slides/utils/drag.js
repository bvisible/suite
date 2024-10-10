import { ref } from 'vue'

export const useDragAndDrop = (target, element) => {
	const isDragging = ref(false)
	const mouseX = ref(0)
	const mouseY = ref(0)

	const startDragging = (e) => {
		isDragging.value = true
		mouseX.value = e.clientX
		mouseY.value = e.clientY
		window.addEventListener('mousemove', drag)
		window.addEventListener('mouseup', stopDragging)
	}

	const drag = (e) => {
		if (isDragging.value) {
			const dx = mouseX.value - e.clientX
			const dy = mouseY.value - e.clientY

			element.left = element.left - dx
			element.top = element.top - dy

			mouseX.value = e.clientX
			mouseY.value = e.clientY
		}
	}

	const stopDragging = (e) => {
		isDragging.value = false
		window.removeEventListener('mousemove', drag)
		window.removeEventListener('mouseup', stopDragging)
	}

	target.addEventListener('mousedown', startDragging)
}
