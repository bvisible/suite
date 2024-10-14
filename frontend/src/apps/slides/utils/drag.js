import { watch, ref } from 'vue'

export const useDragAndDrop = () => {
	const isDragging = ref(false)
	const mouseX = ref(0)
	const mouseY = ref(0)
	const dragTarget = ref(null)
	const dragPosition = ref({ left: 0, top: 0 })

	const startDragging = (e) => {
		e.preventDefault()
		isDragging.value = true
		mouseX.value = e.clientX
		mouseY.value = e.clientY
		window.addEventListener('mousemove', drag)
		window.addEventListener('mouseup', stopDragging)
	}

	const drag = (e) => {
		e.preventDefault()
		if (isDragging.value) {
			const dx = mouseX.value - e.clientX
			const dy = mouseY.value - e.clientY

			dragPosition.value = {
				left: dragPosition.value.left - dx,
				top: dragPosition.value.top - dy,
			}

			mouseX.value = e.clientX
			mouseY.value = e.clientY
		}
	}

	const stopDragging = (e) => {
		e.preventDefault()
		isDragging.value = false
		window.removeEventListener('mousemove', drag)
		window.removeEventListener('mouseup', stopDragging)
	}

	watch(
		() => dragTarget.value,
		(newVal, oldVal) => {
			oldVal?.removeEventListener('mousedown', startDragging)
			newVal?.addEventListener('mousedown', startDragging)
		},
		{ immediate: true },
	)

	return { dragTarget, dragPosition }
}
