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

const actionOrder = {
	execute: {
		addSlide: ['execute', 'jumpToSlide'],
		removeSlide: ['jumpToSlide', 'execute'],
		addElement: ['jumpToSlide', 'execute', 'jumpToElements'],
		removeElement: ['jumpToSlide', 'execute'],
		editElement: ['jumpToSlide', 'jumpToElements', 'execute'],
		batch: ['execute', 'jumpToSlide', 'jumpToElements'],
		editSlide: ['jumpToSlide', 'execute'],
		reorderSlides: ['execute', 'jumpToSlide'],
	},
	undo: {
		addSlide: ['jumpToSlide', 'undo'],
		removeSlide: ['undo', 'jumpToSlide'],
		addElement: ['jumpToSlide', 'undo'],
		removeElement: ['jumpToSlide', 'undo', 'jumpToElements'],
		editElement: ['jumpToSlide', 'jumpToElements', 'undo'],
		batch: ['jumpToSlide', 'jumpToElements', 'undo'],
		editSlide: ['jumpToSlide', 'undo'],
		reorderSlides: ['undo', 'jumpToSlide'],
	},
}

export const useCommandHistory = (state) => {
	const recentlyRestored = ref(false)
	const prevCommands = ref([])
	const nextCommands = ref([])

	const canUndo = computed(() => prevCommands.value.length > 0)
	const canRedo = computed(() => nextCommands.value.length > 0)

	const getActionSequence = (commandKey, operation) => {
		// since redo performs same action as execute
		const op = operation === 'redo' ? 'execute' : operation
		return actionOrder[op]?.[commandKey]
	}

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

	const getSlideIndexForJump = (action, command, operation) => {
		if (action !== 'jumpToSlide') return null

		if (['addSlide', 'removeSlide'].includes(command.key)) {
			if (['execute', 'redo'].includes(operation)) return command.jumpToSlideIndex
			if (operation === 'undo') return command.fromSlideIndex
			return null
		}

		if (command.key == 'reorderSlides') {
			if (['execute', 'redo'].includes(operation)) return command.jumpToSlideIndex
			if (operation === 'undo') return command.fromSlideIndex
			return null
		}

		return slides.value.findIndex((s) => s.clientId === command.jumpToSlideId)
	}

	const handleJumpToSlide = async (action, command, operation) => {
		const slideIdx = getSlideIndexForJump(action, command, operation)

		await jumpToSlide(slideIdx)

		updateThumbnail(slideIdx)
	}

	const executeAction = async (action, command, operation) => {
		switch (action) {
			case 'execute':
				command.execute(state.value)
				break
			case 'undo':
				command.undo(state.value)
				break
			case 'jumpToSlide':
				await handleJumpToSlide(action, command, operation)
				break
			case 'jumpToElements':
				jumpToElements(command.jumpToElementIds, command.focusElementId)
				break
			default:
				break
		}
	}

	const execute = async (command) => {
		const sequence = getActionSequence(command.key, 'execute')
		for (const action of sequence) {
			await executeAction(action, command, 'execute')
		}

		prevCommands.value.push(command)
		nextCommands.value = []
	}

	const undo = async () => {
		if (!canUndo.value) return

		const command = prevCommands.value.pop()

		const sequence = getActionSequence(command.key, 'undo')
		for (const action of sequence) {
			await executeAction(action, command, 'undo')
		}

		nextCommands.value.push(command)
	}

	const redo = async () => {
		if (!canRedo.value) return

		const command = nextCommands.value.pop()

		const sequence = getActionSequence(command.key, 'redo')
		for (const action of sequence) {
			await executeAction(action, command, 'redo')
		}

		prevCommands.value.push(command)
	}

	const clearHistory = () => {
		prevCommands.value = []
		nextCommands.value = []
	}

	return {
		execute,
		undo,
		redo,
		canUndo,
		canRedo,
		prevCommands,
		nextCommands,
		recentlyRestored,
		clearHistory,
	}
}
