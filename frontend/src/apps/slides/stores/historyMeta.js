import { ref, nextTick } from 'vue'
import {
	activeElementIds,
	cropSelectionToFitContent,
	focusElementId,
	setActiveElements,
} from '@/stores/element'
import { changeEditorSlide, currentSlide, slideIndex, slides } from '@/stores/slide'

let commandHistory = null

const setCommandHistory = (history) => {
	commandHistory = history
}

const recentlyRestored = ref(false)

const actionOrder = {
	execute: {
		addSlide: ['execute', 'jumpToSlide'],
		removeSlide: ['jumpToSlide', 'execute'],
		addElement: ['jumpToSlide', 'execute', 'jumpToElements'],
		removeElement: ['jumpToSlide', 'execute'],
		editElement: ['jumpToSlide', 'jumpToElements', 'execute'],
		batch: ['execute', 'jumpToSlide', 'jumpToElements'],
		editSlide: ['execute', 'jumpToSlide'],
		reorderSlides: ['execute', 'jumpToSlide'],
	},
	undo: {
		addSlide: ['jumpToSlide', 'undo'],
		removeSlide: ['undo', 'jumpToSlide'],
		addElement: ['jumpToSlide', 'undo'],
		removeElement: ['jumpToSlide', 'undo', 'jumpToElements'],
		editElement: ['jumpToSlide', 'jumpToElements', 'undo'],
		batch: ['jumpToSlide', 'undo', 'jumpToElements'],
		editSlide: ['undo', 'jumpToSlide'],
		reorderSlides: ['undo', 'jumpToSlide'],
	},
}

const jumpToSlideByIndex = async (index, focus) => {
	const onActiveSlide = index === slideIndex.value

	if (!onActiveSlide && index != null) {
		await changeEditorSlide(index, focus)

		recentlyRestored.value = true
		setTimeout(() => {
			recentlyRestored.value = false
		}, 1000)
	}
}

const jumpToElementsByIds = (jumpToIds, focusOnId) => {
	if (!jumpToIds || jumpToIds.length === 0) return

	const elementExists = jumpToIds.every((id) =>
		currentSlide.value?.elements?.some((el) => el.id === id),
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

const handleJumpToSlide = (action, command, operation) => {
	const slideIdx = getSlideIndexForJump(action, command, operation)
	const focus = command.key === 'removeSlide' && operation === 'undo' ? false : true

	return jumpToSlideByIndex(slideIdx, focus)
}

const handleJumpToElements = (action, command, operation) => {
	const jumpToIds = command.jumpToElementIds
	const focusOnId = command.focusElementId

	jumpToElementsByIds(jumpToIds, focusOnId)
}

const actions = {
	jumpToSlide: handleJumpToSlide,
	jumpToElements: handleJumpToElements,
}

export { commandHistory, recentlyRestored, actionOrder, actions, setCommandHistory }
