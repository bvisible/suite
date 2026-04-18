import { findElement } from '@/stores/element'

const findSlide = (state, slideId) => state.find((s) => s.name === slideId)

export const addElementCommand = ({ slideId, element }) => ({
	slideId,
	elementIds: [element.id],
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
	slideId,
	elementIds: [element.id],
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

export const editElementCommand = ({ slideId, elementIds, property, oldValue, newValue }) => {
	return {
		slideId,
		elementIds,
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
	}
}

export const batchCommand = ({ slideId, elementIds, commands }) => ({
	slideId,
	elementIds,
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
