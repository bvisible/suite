import { ref, computed, nextTick } from 'vue'
import {
	activeElementIds,
	cropSelectionToFitContent,
	focusElementId,
	setActiveElements,
} from '@/stores/element'
import {
	changeEditorSlide,
	currentSlide,
	slideIndex,
	slides,
	updateThumbnail,
} from '@/stores/slide'

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

	const jumpToElements = (jumpToIds, focusOnId) => {
		if (!jumpToIds || jumpToIds.length === 0) return
		const elementExists = jumpToIds.every((id) =>
			currentSlide.value?.elements.some((el) => el.id === id),
		)
		if (!elementExists) {
			activeElementIds.value = []
			return
		}
		if (JSON.stringify(activeElementIds.value) !== JSON.stringify(jumpToIds)) {
			nextTick(() => {
				setActiveElements(jumpToIds)
				if (focusOnId) {
					focusElementId.value = focusOnId
				}
			})
		} else {
			cropSelectionToFitContent(jumpToIds)
		}
	}

	const execute = async (command) => {
		command.execute(state.value)
		prevCommands.value.push(command)
		nextCommands.value = []

		let index = null
		if (command.key === 'addSlide') {
			index = command.jumpToSlideIndex
		} else {
			index = slides.value.findIndex((s) => s.name === command.jumpToSlideId)
		}

		await jumpToSlide(index)
		updateThumbnail(index)
		jumpToElements(command.jumpToElementIds, command.focusElementId)
	}

	const undo = async () => {
		if (!canUndo.value) return

		const command = prevCommands.value.pop()

		let index = null

		if (command.key === 'addSlide') {
			index = command.fromSlideIndex
			await jumpToSlide(index)
			command.undo(state.value)
			nextCommands.value.push(command)
		} else {
			index = slides.value.findIndex((s) => s.name === command.jumpToSlideId)
			await jumpToSlide(index)
			command.undo(state.value)
			nextCommands.value.push(command)
		}

		updateThumbnail(index)

		jumpToElements(command.jumpToElementIds, command.focusElementId)
	}

	const redo = async () => {
		if (!canRedo.value) return

		const command = nextCommands.value.pop()

		let index = null

		if (command.key === 'addSlide') {
			index = command.jumpToSlideIndex
			command.execute(state.value)
			await jumpToSlide(index)
			prevCommands.value.push(command)
		} else {
			index = slides.value.findIndex((s) => s.name === command.jumpToSlideId)
			await jumpToSlide(command.slideId)
			command.execute(state.value)
			prevCommands.value.push(command)
		}

		updateThumbnail(index)

		jumpToElements(command.jumpToElementIds, command.focusElementId)
	}

	return { execute, undo, redo, canUndo, canRedo, prevCommands, nextCommands, recentlyRestored }
}
