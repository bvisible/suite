import { findElement } from '@/stores/element'
import { slidesLength } from '@/stores/presentation'

const findSlide = (state, slideId) => state.find((s) => s.clientId === slideId)

const addElement = (state, slideId, element) => {
	const slide = findSlide(state, slideId)
	if (!slide) return
	if (slide.elements.find((el) => el.id === element.id)) return
	slide.elements.push(element)
}

const removeElement = (state, slideId, element) => {
	const slide = findSlide(state, slideId)
	if (!slide) return
	slide.elements = slide.elements.filter((el) => el.id !== element.id)
}

const addElementCommand = ({ slideId, element }) => ({
	key: 'addElement',
	jumpToSlideId: slideId,
	jumpToElementIds: [element.id],
	focusElementId: element.type === 'text' ? element.id : null,
	debug: `Add element ${element.id} on slide ${slideId}`,
	execute(state) {
		addElement(state, slideId, element)
	},
	undo(state) {
		removeElement(state, slideId, element)
	},
})

const removeElementCommand = ({ slideId, element }) => ({
	key: 'removeElement',
	jumpToSlideId: slideId,
	jumpToElementIds: [element.id],
	focusElementId: element.type === 'text' ? element.id : null,
	debug: `Remove element ${element.id} on slide ${slideId}`,
	execute(state) {
		removeElement(state, slideId, element)
	},
	undo(state) {
		addElement(state, slideId, element)
	},
})

const editElements = (state, slideId, elementIds, property, value) => {
	elementIds.forEach((elementId) => {
		findElement(state, slideId, elementId)[property] = value
	})
}

const editElementCommand = ({ slideId, elementIds, property, oldValue, newValue }) => ({
	key: 'editElement',
	jumpToSlideId: slideId,
	jumpToElementIds: elementIds,
	debug: `Edit ${property} of element ${elementIds} on slide ${slideId} to ${newValue}`,
	execute(state) {
		editElements(state, slideId, elementIds, property, newValue)
	},
	undo(state) {
		editElements(state, slideId, elementIds, property, oldValue)
	},
})

const addSlide = (state, index, slide) => {
	state.splice(index, 0, slide)
	state.forEach((slide, idx) => {
		slide.idx = idx + 1
	})
	slidesLength.value = state.length
}

const removeSlide = (state, index, slide) => {
	const idx = state.findIndex((s) => s.clientId === slide.clientId)
	if (idx !== -1) state.splice(idx, 1)
	state.forEach((slide, idx) => {
		slide.idx = idx + 1
	})
	slidesLength.value = state.length
}

const addSlideCommand = ({ slide, index, slideIndex }) => ({
	key: 'addSlide',
	jumpToSlideIndex: index,
	fromSlideIndex: slideIndex,
	debug: `Add slide ${slide.clientId} at index ${index}`,
	execute(state) {
		addSlide(state, index, slide)
	},
	undo(state) {
		removeSlide(state, index, slide)
	},
})

const removeSlideCommand = ({ slide, index, slideIndex }) => ({
	key: 'removeSlide',
	jumpToSlideIndex: index - 1,
	fromSlideIndex: slideIndex,
	debug: `Remove slide at index ${index}`,
	execute(state) {
		removeSlide(state, index, slide)
	},
	undo(state) {
		addSlide(state, index, slide)
	},
})

const editSlide = (state, slideId, property, value) => {
	const slide = state.find((s) => s.clientId === slideId)
	if (slide) slide[property] = value
}

const editSlideCommand = ({ slideId, property, oldValue, newValue }) => ({
	key: 'editSlide',
	jumpToSlideId: slideId,
	debug: `Edit ${property} of slide ${slideId} to ${newValue}`,
	execute(state) {
		editSlide(state, slideId, property, newValue)
	},
	undo(state) {
		editSlide(state, slideId, property, oldValue)
	},
})

const moveSlide = (state, fromIndex, toIndex) => {
	const [movedSlide] = state.splice(fromIndex, 1)
	state.splice(toIndex, 0, movedSlide)
	state.forEach((slide, idx) => {
		slide.idx = idx + 1
	})
}

const reorderSlidesCommand = ({ oldIndex, newIndex }) => ({
	key: 'reorderSlides',
	fromSlideIndex: oldIndex,
	jumpToSlideIndex: newIndex,
	debug: `Reorder slide from index ${oldIndex} to ${newIndex}`,
	execute(state) {
		moveSlide(state, oldIndex, newIndex)
	},
	undo(state) {
		moveSlide(state, newIndex, oldIndex)
	},
})

const batchCommand = ({ slideId, elementIds, focusElementId, commands }) => ({
	key: 'batch',
	jumpToSlideId: slideId,
	jumpToElementIds: elementIds,
	focusElementId: focusElementId,
	debug: 'Batch edit',
	execute: (state) => {
		commands.forEach((c) => c.execute(state))
	},
	undo: (state) => {
		commands
			.slice()
			.reverse()
			.forEach((c) => c.undo(state))
	},
})

export {
	addElementCommand,
	removeElementCommand,
	editElementCommand,
	addSlideCommand,
	removeSlideCommand,
	editSlideCommand,
	reorderSlidesCommand,
	batchCommand,
}
