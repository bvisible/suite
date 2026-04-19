import { findElement } from '@/stores/element'
import { slidesLength } from '@/stores/presentation'

const findSlide = (state, slideId) => state.find((s) => s.name === slideId)

export const addElementCommand = ({ slideId, element }) => ({
	key: 'addElement',
	jumpToSlideId: slideId,
	jumpToElementIds: [element.id],
	focusElementId: element.type === 'text' ? element.id : null,
	debug: `Add element ${element.id} on slide ${slideId}`,
	execute(state) {
		const slide = findSlide(state, slideId)
		if (!slide) return
		if (slide.elements.find((el) => el.id === element.id)) return
		slide.elements.push(element)
	},
	undo(state) {
		const slide = findSlide(state, slideId)
		if (!slide) return
		slide.elements = slide.elements.filter((el) => el.id !== element.id)
	},
})

export const removeElementCommand = ({ slideId, element }) => ({
	key: 'removeElement',
	jumpToSlideId: slideId,
	jumpToElementIds: [element.id],
	focusElementId: element.type === 'text' ? element.id : null,
	debug: `Remove element ${element.id} on slide ${slideId}`,
	execute(state) {
		const slide = findSlide(state, slideId)
		if (!slide) return
		slide.elements = slide.elements.filter((el) => el.id !== element.id)
	},
	undo(state) {
		const slide = findSlide(state, slideId)
		if (!slide) return
		if (slide.elements.find((el) => el.id === element.id)) return
		slide.elements.push(element)
	},
})

export const editElementCommand = ({ slideId, elementIds, property, oldValue, newValue }) => ({
	key: 'editElement',
	jumpToSlideId: slideId,
	jumpToElementIds: elementIds,
	debug: `Edit ${property} of element ${elementIds} on slide ${slideId} to ${newValue}`,
	execute(state) {
		elementIds.forEach((elementId) => {
			findElement(state, slideId, elementId)[property] = newValue
		})
	},
	undo(state) {
		elementIds.forEach((elementId) => {
			findElement(state, slideId, elementId)[property] = oldValue
		})
	},
})

export const batchCommand = ({ slideId, elementIds, commands }) => ({
	key: 'batch',
	jumpToSlideId: slideId,
	jumpToElementIds: elementIds,
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

export const addSlideCommand = ({ slide, index, slideIndex }) => ({
	key: 'addSlide',
	jumpToSlideIndex: index,
	fromSlideIndex: slideIndex,
	debug: `Add slide ${slide.name} at index ${index}`,
	execute(state) {
		slide.name = ''
		state.splice(index, 0, slide)
		state.forEach((slide, idx) => {
			slide.idx = idx + 1
		})
		slidesLength.value = state.length
	},
	undo(state) {
		const idx = state.findIndex((s) => s.name === slide.name)
		if (idx !== -1) state.splice(idx, 1)
		state.forEach((slide, idx) => {
			slide.idx = idx + 1
		})
		slidesLength.value = state.length
	},
})

export const removeSlideCommand = ({ slide, index, slideIndex }) => ({
	key: 'removeSlide',
	jumpToSlideIndex: index - 1,
	fromSlideIndex: slideIndex,
	debug: `Remove slide at index ${index}`,
	execute(state) {
		const idx = state.findIndex((s) => s.name === slide.name)
		if (idx !== -1) state.splice(idx, 1)
		state.forEach((slide, idx) => {
			slide.idx = idx + 1
		})
		slidesLength.value = state.length
	},
	undo(state) {
		slide.name = ''
		state.splice(index, 0, slide)
		state.forEach((slide, idx) => {
			slide.idx = idx + 1
		})

		slidesLength.value = state.length
	},
})
