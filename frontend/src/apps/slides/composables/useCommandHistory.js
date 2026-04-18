import { ref, computed } from 'vue'
import { activeElementIds, cropSelectionToFitContent, focusElementId } from '@/stores/element'
import { changeEditorSlide, currentSlide, slideIndex, slides } from '@/stores/slide'

export const useCommandHistory = (state) => {
	const recentlyRestored = ref(false)
	const prevCommands = ref([])
	const nextCommands = ref([])

	const canUndo = computed(() => prevCommands.value.length > 0)
	const canRedo = computed(() => nextCommands.value.length > 0)

	const jumpToSlide = async (index) => {
		const onActiveSlide = index === slideIndex.value

		if (!onActiveSlide && index != null) {
			await changeEditorSlide(index, false)

			recentlyRestored.value = true
			setTimeout(() => {
				recentlyRestored.value = false
			}, 1000)
		}
	}

	const jumpToElements = (jumpToElementIds) => {
		if (!jumpToElementIds || jumpToElementIds.length === 0) return
		const elementExists = jumpToElementIds.every((id) =>
			currentSlide.value?.elements.some((el) => el.id === id),
		)
		if (!elementExists) {
			activeElementIds.value = []
			return
		}
		if (JSON.stringify(activeElementIds.value) !== JSON.stringify(jumpToElementIds)) {
			focusElementId.value = null
			activeElementIds.value = jumpToElementIds
		} else {
			cropSelectionToFitContent(jumpToElementIds)
		}
	}

	const execute = (command) => {
		command.execute(state.value)
		prevCommands.value.push(command)
		nextCommands.value = []
	}

	const undo = async () => {
		if (!canUndo.value) return

		const command = prevCommands.value.pop()

		if (command.key === 'addSlide') {
			const index = command.fromSlideIndex
			await jumpToSlide(index)
			command.undo(state.value)
			nextCommands.value.push(command)
		} else {
			const index = slides.value.findIndex((s) => s.name === command.jumpToSlideId)
			await jumpToSlide(index)
			command.undo(state.value)
			nextCommands.value.push(command)
		}

		jumpToElements(command.elementIds)
	}

	const redo = async () => {
		if (!canRedo.value) return

		const command = nextCommands.value.pop()

		if (command.key === 'addSlide') {
			const index = command.jumpToSlideIndex
			command.execute(state.value)
			await jumpToSlide(index)
			prevCommands.value.push(command)
		} else {
			const index = slides.value.findIndex((s) => s.name === command.jumpToSlideId)
			await jumpToSlide(command.slideId)
			command.execute(state.value)
			prevCommands.value.push(command)
		}

		jumpToElements(command.elementIds)
	}

	return { execute, undo, redo, canUndo, canRedo, prevCommands, nextCommands, recentlyRestored }
}
